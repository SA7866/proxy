// customise.js — Product Customiser
//
// This file controls the entire canvas-based design editor in the browser.
// It uses the HTML5 Canvas API — think of canvas as a whiteboard you can
// draw on using JavaScript.
// MDN Canvas API docs: https://developer.mozilla.org/en-US/docs/Web/API/Canvas_API
//
// Features:
//   - Add text (font, size, bold, italic, colour, background colour)
//   - Upload an image onto the product
//   - Drag and resize elements with the mouse
//   - Change the shirt/product colour (using pixel-level multiply blending)
//   - Undo (Ctrl+Z) — snaps back to the previous state
//   - Duplicate, bring to front, send to back
//   - Save — sends the design as JSON to Django, which stores it in the database


// -------------------------------------------------------
// DOM REFERENCES
// getElementById finds an HTML element on the page by its id attribute.
// We store references here so we don't have to search the page on every draw call.
// -------------------------------------------------------
const canvas = document.getElementById("designerCanvas");
// getContext("2d") returns the 2D drawing context used for all canvas operations.
// MDN: https://developer.mozilla.org/en-US/docs/Web/API/HTMLCanvasElement/getContext
const ctx    = canvas.getContext("2d");

// These two values are injected by the Django template (see customise.html):
//   window.PRODUCT_TEMPLATE_URL — URL of the transparent product PNG
//   window.PRINT_AREA           — {x, y, w, h} rectangle where designs are allowed
const templateUrl = window.PRODUCT_TEMPLATE_URL;
const printArea   = window.PRINT_AREA;

// --- Text controls ---
const addTextBtn      = document.getElementById("addTextBtn");
const textInput       = document.getElementById("textInput");
const textSizeInput   = document.getElementById("textSize");
const textColorInput  = document.getElementById("textColor");
const fontFamilySelect = document.getElementById("fontFamily");
const boldToggle      = document.getElementById("boldToggle");
const italicToggle    = document.getElementById("italicToggle");
const textBgCheck     = document.getElementById("textBgCheck");
const textBgColor     = document.getElementById("textBgColor");

// --- Image upload ---
const imageInput = document.getElementById("imageInput");

// --- Element controls (apply to whichever element is selected) ---
const opacitySlider  = document.getElementById("opacitySlider");
const opacityValue   = document.getElementById("opacityValue");
const rotationSlider = document.getElementById("rotationSlider");
const rotationValue  = document.getElementById("rotationValue");
const deleteBtn     = document.getElementById("deleteBtn");
const duplicateBtn  = document.getElementById("duplicateBtn");
const sendBackBtn   = document.getElementById("sendBackBtn");
const bringFrontBtn = document.getElementById("bringFrontBtn");
const undoBtn       = document.getElementById("undoBtn");

// --- Shirt colour ---
const shirtColorInput    = document.getElementById("shirtColorInput");
const resetShirtColorBtn = document.getElementById("resetShirtColorBtn");

// --- Save form hidden fields ---
// These hidden <input> fields carry data from JavaScript to Django when the form is submitted
const saveForm        = document.getElementById("saveForm");
const designDataField = document.getElementById("designData");      // JSON string of all elements
const previewField    = document.getElementById("previewDataUrl");  // base64 PNG screenshot
const sizeSelect      = document.getElementById("sizeSelect");
const sizeField       = document.getElementById("sizeField");


// -------------------------------------------------------
// STATE
// These variables track what's happening on the canvas at any given moment.
// -------------------------------------------------------
const elements  = [];     // array of all design elements (text and image objects)
let selectedId  = null;   // id of the currently selected element (null = nothing selected)
let isDragging  = false;  // true while the user is dragging an element
let isResizing  = false;  // true while the user is dragging the resize handle
let dragOffsetX = 0;      // distance from mouse to element's left edge when drag started
let dragOffsetY = 0;      // distance from mouse to element's top edge when drag started
let didChange   = false;  // becomes true if the mouse actually moved during a drag
let syncingControls = false; // used to prevent toolbar updates triggering themselves in a loop
let shirtColor = null;    // the chosen shirt colour (null = white, no tint)

// --- Background mask + colour cache (built once from the template image) ---
let backgroundMask          = null; // stores which pixels are background (not shirt)
let coloredTemplateCache    = null; // pre-tinted version of the template image
let coloredTemplateCacheKey = null; // the colour used to build the cache above

const TEXT_PAD    = 8;   // pixels of padding inside text boxes
const MIN_BOX     = 30;  // minimum width/height for any element
const MAX_HISTORY = 40;  // maximum number of undo steps stored

// Undo stack — each entry is a full snapshot of the canvas state at a point in time
const history = [];


// -------------------------------------------------------
// TEMPLATE IMAGE
// Load the product's transparent PNG template.
// Once it's fully loaded (onload), compute the background mask and then draw.
// -------------------------------------------------------
const templateImg  = new Image();
// crossOrigin = "anonymous" allows canvas to read pixel data from Cloudinary-hosted images.
// Without this, reading pixels from a cross-origin image would throw a SecurityError.
// MDN: https://developer.mozilla.org/en-US/docs/Web/HTML/CORS_enabled_image
templateImg.crossOrigin = "anonymous";
templateImg.src    = templateUrl;
templateImg.onload = () => {
  // Build the background mask once — tells us which pixels are shirt vs background
  backgroundMask = computeBackgroundMask();

  if (window.INITIAL_DESIGN) {
    // "Edit Again" was clicked — restore the previously saved design
    applySnapshot({
      els:        window.INITIAL_DESIGN.elements || [],
      shirtColor: window.INITIAL_DESIGN.shirtColor || null,
    });
  } else {
    // Fresh canvas — push an empty starting state so Ctrl+Z can't go further back
    pushHistory();
    draw();
  }
};


// -------------------------------------------------------
// BACKGROUND MASK
//
// The template image is a transparent PNG of the product (e.g. a jumper).
// We need to know which pixels are "shirt" vs "background" so that when the
// user picks a shirt colour we only tint the shirt, not the white space around it.
//
// HOW IT WORKS (flood fill / BFS):
//   1. We draw the template onto an offscreen (hidden) canvas and read its pixels.
//   2. We start from every edge pixel that is whitish (near-white colour).
//   3. We "flood fill" outward through connected whitish pixels — like the paint
//      bucket tool in MS Paint, but starting from the border.
//   4. Any pixel the fill reaches is "background". Pixels it can't reach (blocked
//      by the shirt outline) are "shirt pixels".
//   5. The result is a Uint8Array (fast lookup array): 1 = background, 0 = shirt.
// -------------------------------------------------------
function computeBackgroundMask() {
  const w = canvas.width;
  const h = canvas.height;

  // Draw the template onto a hidden canvas so we can read its pixel colours
  const off = document.createElement("canvas");
  off.width  = w;
  off.height = h;
  const offCtx = off.getContext("2d");
  offCtx.drawImage(templateImg, 0, 0, w, h);
  // getImageData returns a flat array: [R,G,B,A, R,G,B,A, ...] for every pixel
  const data = offCtx.getImageData(0, 0, w, h).data;

  const mask    = new Uint8Array(w * h); // final result: 1 = background pixel
  const visited = new Uint8Array(w * h); // tracks which pixels we've already checked

  // A pixel is "whitish" if its red, green, and blue are all above 235 (near white)
  function isWhitish(pixelIdx) {
    const i = pixelIdx * 4; // each pixel takes 4 slots: R, G, B, A
    return data[i] > 235 && data[i + 1] > 235 && data[i + 2] > 235;
  }

  // Seed the queue with all edge pixels that are whitish (the background border)
  const queue = [];
  for (let x = 0; x < w; x++) {
    for (const y of [0, h - 1]) {       // top and bottom rows
      const idx = y * w + x;
      if (isWhitish(idx)) queue.push(idx);
    }
  }
  for (let y = 1; y < h - 1; y++) {
    for (const x of [0, w - 1]) {       // left and right columns
      const idx = y * w + x;
      if (isWhitish(idx)) queue.push(idx);
    }
  }

  // BFS (Breadth-First Search) — process the queue, spreading to neighbours
  let head = 0;
  while (head < queue.length) {
    const idx = queue[head++]; // take the next pixel from the front of the queue
    if (visited[idx]) continue; // already processed — skip
    if (!isWhitish(idx)) continue; // not white — this is the shirt edge, stop spreading
    visited[idx] = 1;
    mask[idx]    = 1; // mark as background

    // Add the 4 neighbouring pixels (up/down/left/right) to check next
    const x = idx % w;
    const y = Math.floor(idx / w);
    if (x > 0)     queue.push(idx - 1); // left
    if (x < w - 1) queue.push(idx + 1); // right
    if (y > 0)     queue.push(idx - w); // up
    if (y < h - 1) queue.push(idx + w); // down
  }

  return mask;
}


// -------------------------------------------------------
// COLOURED TEMPLATE
//
// Applies the user's chosen shirt colour to the template image using
// "multiply blending" — the same blend mode as photo editing apps.
//
// MULTIPLY BLENDING:
//   new_pixel = (original_pixel / 255) × chosen_colour
//   White (255) × any colour = that colour  → shirt becomes the chosen colour
//   Dark pixels (shadows, seams) × colour  = darker version of colour → details preserved
//
// The result is cached in an offscreen canvas.
// If the user picks the same colour twice, we return the cached version instead of
// recalculating (much faster).
// -------------------------------------------------------
function buildColoredTemplate(color) {
  // Return cached version if colour hasn't changed
  if (color === coloredTemplateCacheKey && coloredTemplateCache) {
    return coloredTemplateCache;
  }

  const w = canvas.width;
  const h = canvas.height;

  // Draw the original template onto a new offscreen canvas
  const off = document.createElement("canvas");
  off.width  = w;
  off.height = h;
  const offCtx = off.getContext("2d");
  offCtx.drawImage(templateImg, 0, 0, w, h);

  if (color) {
    // Convert the hex colour string (#rrggbb) into separate R, G, B numbers
    const r = parseInt(color.slice(1, 3), 16); // e.g. "ff" → 255
    const g = parseInt(color.slice(3, 5), 16);
    const b = parseInt(color.slice(5, 7), 16);

    const imgData = offCtx.getImageData(0, 0, w, h);
    const d = imgData.data;

    for (let idx = 0; idx < w * h; idx++) {
      if (backgroundMask[idx]) continue;  // skip — this is background, not shirt
      if (d[idx * 4 + 3] < 10) continue; // skip — transparent pixel

      // Apply multiply blend to this shirt pixel
      const i  = idx * 4;
      d[i]     = Math.round(d[i]     * r / 255); // red channel
      d[i + 1] = Math.round(d[i + 1] * g / 255); // green channel
      d[i + 2] = Math.round(d[i + 2] * b / 255); // blue channel
      // alpha (d[i+3]) is left unchanged
    }

    offCtx.putImageData(imgData, 0, 0);
  }

  // Cache the result so we don't recalculate on every draw() call
  coloredTemplateCache    = off;
  coloredTemplateCacheKey = color;
  return off;
}


// -------------------------------------------------------
// UNDO SYSTEM
//
// Every time the canvas changes (element added, moved, deleted, etc.)
// we call pushHistory() to save a snapshot of the current state.
// When the user presses Ctrl+Z (or clicks Undo), we pop the last snapshot
// and restore it using applySnapshot().
//
// serializeElements() converts the elements array to plain JSON because
// Image objects (used for uploaded photos) can't be stored in JSON directly —
// we store the image's src URL instead and reload it from applySnapshot.
// -------------------------------------------------------
function serializeElements() {
  return elements.map(el => ({
    id: el.id,
    type: el.type,
    x: el.x, y: el.y, w: el.w, h: el.h,
    opacity:  el.opacity  ?? 1,
    rotation: el.rotation ?? 0,
    // Text-specific properties (undefined for image elements)
    text:       el.type === "text" ? el.text       : undefined,
    fontSize:   el.type === "text" ? el.fontSize   : undefined,
    color:      el.type === "text" ? el.color      : undefined,
    fontFamily: el.type === "text" ? el.fontFamily : undefined,
    bold:       el.type === "text" ? el.bold       : undefined,
    italic:     el.type === "text" ? el.italic     : undefined,
    useBg:      el.type === "text" ? el.useBg      : undefined,
    bgColor:    el.type === "text" ? el.bgColor    : undefined,
    // Image-specific: store the URL, not the Image object
    src: el.type === "image" ? el.img?.src : undefined,
  }));
}

// Save the current state to the history stack
function pushHistory() {
  history.push({
    els: serializeElements(),
    shirtColor,
  });
  // Keep the stack from growing too large (remove the oldest entry if needed)
  if (history.length > MAX_HISTORY) history.shift();
}

// Restore a snapshot — we need to rebuild Image objects for image elements
// because JSON only stored the src URL, not the actual loaded image
function applySnapshot(snap) {
  shirtColor = snap.shirtColor ?? null;
  if (shirtColorInput) shirtColorInput.value = shirtColor || "#ffffff";

  const slots = new Array(snap.els.length).fill(null);
  let pending = 0; // counts how many images are still loading

  snap.els.forEach((s, i) => {
    if (s.type === "image" && s.src) {
      // Images must be loaded asynchronously — we wait for all of them before drawing
      pending++;
      const img = new Image();
      img.onload = () => {
        slots[i] = { ...s, img }; // attach the loaded Image object
        if (--pending === 0) finishApply(slots); // all done — apply to canvas
      };
      img.src = s.src;
    } else {
      slots[i] = { ...s }; // text elements don't need async loading
    }
  });

  if (pending === 0) finishApply(slots); // no images — apply immediately
}

// Called once all images in a snapshot have finished loading
function finishApply(slots) {
  elements.length = 0;
  slots.forEach(el => { if (el) elements.push(el); });
  selectedId = null;
  syncOpacityUI();
  draw();
}

// Step back one level in history
function undo() {
  if (history.length <= 1) return; // nothing to undo (can't go before the initial empty state)
  history.pop();
  applySnapshot(history[history.length - 1]);
}

undoBtn.addEventListener("click", undo);
// Ctrl+Z (Windows/Linux) or Cmd+Z (Mac) triggers undo
window.addEventListener("keydown", e => {
  if ((e.ctrlKey || e.metaKey) && e.key === "z") { e.preventDefault(); undo(); }
});


// -------------------------------------------------------
// SHIRT COLOUR
// -------------------------------------------------------
shirtColorInput.addEventListener("input", () => {
  const val = shirtColorInput.value;
  // Treat white as "no colour" so the original template shows through
  shirtColor = (val === "#ffffff") ? null : val;
  if (shirtColor) buildColoredTemplate(shirtColor); // pre-build so draw() is instant
  draw();
});

// Only push to undo history when the user finishes picking (not on every tiny change)
shirtColorInput.addEventListener("change", () => {
  pushHistory();
});

resetShirtColorBtn.addEventListener("click", () => {
  shirtColor = null;
  shirtColorInput.value = "#ffffff";
  pushHistory();
  draw();
});


// -------------------------------------------------------
// FONT HELPER
// Builds a CSS font string like "bold italic 48px Arial" from an element's properties
// -------------------------------------------------------
function buildFont(el) {
  const italic = el.italic ? "italic " : "";
  const bold   = el.bold   ? "bold "   : "";
  return `${italic}${bold}${el.fontSize}px ${el.fontFamily || "Arial"}`;
}


// -------------------------------------------------------
// UTILITY HELPERS
// -------------------------------------------------------

// Clamps a value between min and max (e.g. clamp(150, 0, 100) returns 100)
function clamp(val, min, max) {
  return Math.max(min, Math.min(max, val));
}

// Converts a mouse event's screen position to canvas pixel coordinates.
// Needed because the canvas may be displayed smaller than its actual pixel size.
function getMousePos(evt) {
  const rect   = canvas.getBoundingClientRect(); // size and position of canvas on screen
  const scaleX = canvas.width  / rect.width;    // how many canvas pixels per screen pixel
  const scaleY = canvas.height / rect.height;
  return {
    x: (evt.clientX - rect.left) * scaleX,
    y: (evt.clientY - rect.top)  * scaleY,
  };
}

// Returns the currently selected element object, or null if nothing is selected
function getSelected() {
  return elements.find(e => e.id === selectedId) || null;
}

// Keeps an element inside the print area — prevents designs going outside the printable zone
function clampToPrintArea(el) {
  el.x = clamp(el.x, printArea.x, printArea.x + printArea.w - el.w);
  el.y = clamp(el.y, printArea.y, printArea.y + printArea.h - el.h);
}

// Returns true if the point (x, y) is inside the element's bounding box
function hitTest(el, x, y) {
  return x >= el.x && x <= el.x + el.w && y >= el.y && y <= el.y + el.h;
}

// Returns true if the point (x, y) is inside the resize handle (bottom-right corner)
function hitResizeHandle(el, x, y) {
  const size = 14; // size of the square resize handle in pixels
  return x >= el.x + el.w - size && x <= el.x + el.w
      && y >= el.y + el.h - size && y <= el.y + el.h;
}

// Measures the pixel width and height needed to display a text element,
// then updates el.w and el.h accordingly so the box fits the text exactly
function measureTextBox(el) {
  ctx.save();
  ctx.font = buildFont(el);
  const m       = ctx.measureText(el.text);
  const ascent  = m.actualBoundingBoxAscent  ?? el.fontSize * 0.8;
  const descent = m.actualBoundingBoxDescent ?? el.fontSize * 0.2;
  el.w = Math.max(60, Math.ceil(m.width         + TEXT_PAD * 2));
  el.h = Math.max(40, Math.ceil(ascent + descent + TEXT_PAD * 2));
  ctx.restore();
  clampToPrintArea(el);
}

// Positions an element so it appears in the centre of the print area
function centreInPrintArea(el) {
  el.x = printArea.x + (printArea.w - el.w) / 2;
  el.y = printArea.y + (printArea.h - el.h) / 2;
  clampToPrintArea(el);
}

// Finds the largest font size (starting from 160px down to 10px) where the
// text still fits inside the print area — used to cap the size slider
function maxFontSizeForText(el) {
  for (let size = 160; size >= 10; size--) {
    ctx.save();
    ctx.font = buildFont({ ...el, fontSize: size });
    const m       = ctx.measureText(el.text);
    const ascent  = m.actualBoundingBoxAscent  ?? size * 0.8;
    const descent = m.actualBoundingBoxDescent ?? size * 0.2;
    const fits    = (m.width + TEXT_PAD * 2) <= printArea.w
                 && (ascent + descent + TEXT_PAD * 2) <= printArea.h;
    ctx.restore();
    if (fits) return size;
  }
  return 10;
}


// -------------------------------------------------------
// OPACITY + ROTATION SLIDERS
// When the user moves a slider, update the selected element and redraw.
// -------------------------------------------------------
function syncOpacityUI() {
  const el  = getSelected();
  const val = el ? Math.round((el.opacity ?? 1) * 100) : 100;
  opacitySlider.value      = val;
  opacityValue.textContent = val + "%";
  const rot = el ? (el.rotation ?? 0) : 0;
  rotationSlider.value      = rot;
  rotationValue.textContent = rot + "°";
}

opacitySlider.addEventListener("input", () => {
  const val = parseInt(opacitySlider.value) / 100;
  opacityValue.textContent = opacitySlider.value + "%";
  const el = getSelected();
  if (el) { el.opacity = val; draw(); }
});

opacitySlider.addEventListener("change", () => {
  if (getSelected()) pushHistory();
});

rotationSlider.addEventListener("input", () => {
  const deg = parseInt(rotationSlider.value);
  rotationValue.textContent = deg + "°";
  const el = getSelected();
  if (el) { el.rotation = deg; draw(); }
});

rotationSlider.addEventListener("change", () => {
  if (getSelected()) pushHistory(); // save undo state when slider is released
});


// -------------------------------------------------------
// DRAWING
// draw() redraws the entire canvas from scratch on every change.
// Canvas doesn't remember what was drawn — we repaint everything each time.
// -------------------------------------------------------

// Draws the blue dashed rectangle showing the printable area boundary
function drawPrintArea() {
  ctx.save();
  ctx.setLineDash([8, 6]);      // dashed line: 8px dash, 6px gap
  ctx.strokeStyle = "#2b67ff";
  ctx.lineWidth   = 2;
  ctx.strokeRect(printArea.x, printArea.y, printArea.w, printArea.h);
  ctx.restore();
}

// Draws one element (text or image) onto the canvas
// MDN ctx.rotate: https://developer.mozilla.org/en-US/docs/Web/API/CanvasRenderingContext2D/rotate
function drawElement(el) {
  ctx.save();

  // Apply rotation around the element's centre point
  if (el.rotation) {
    const cx = el.x + el.w / 2;
    const cy = el.y + el.h / 2;
    ctx.translate(cx, cy);
    ctx.rotate((el.rotation * Math.PI) / 180); // convert degrees to radians
    ctx.translate(-cx, -cy);
  }

  ctx.globalAlpha = el.opacity ?? 1;

  // If this element is selected, draw a blue selection border and resize handle
  if (el.id === selectedId) {
    ctx.globalAlpha = 1;
    ctx.strokeStyle = "#2563eb";
    ctx.lineWidth   = 2;
    ctx.strokeRect(el.x, el.y, el.w, el.h);
    ctx.fillStyle = "#2563eb";
    ctx.fillRect(el.x + el.w - 14, el.y + el.h - 14, 14, 14);
    ctx.globalAlpha = el.opacity ?? 1;
  }

  if (el.type === "text") {
    if (el.useBg && el.bgColor) {
      ctx.fillStyle = el.bgColor;
      ctx.fillRect(el.x, el.y, el.w, el.h);
    }
    ctx.font         = buildFont(el);
    ctx.fillStyle    = el.color;
    ctx.textBaseline = "top";
    ctx.fillText(el.text, el.x + TEXT_PAD, el.y + TEXT_PAD);
  }

  if (el.type === "image" && el.img) {
    ctx.drawImage(el.img, el.x, el.y, el.w, el.h);
  }

  ctx.restore();
}

// Main draw function — clears canvas and repaints everything
function draw() {
  ctx.clearRect(0, 0, canvas.width, canvas.height); // wipe the canvas

  // Draw the product template (tinted if a colour is chosen, original otherwise)
  if (shirtColor) {
    ctx.drawImage(buildColoredTemplate(shirtColor), 0, 0);
  } else {
    ctx.drawImage(templateImg, 0, 0, canvas.width, canvas.height);
  }

  drawPrintArea(); // blue dashed rectangle showing where designs can go
  for (const el of elements) drawElement(el); // draw all design elements on top
}


// -------------------------------------------------------
// TOOLBAR ↔ ELEMENT SYNC
//
// When a text element is selected, i update the toolbar controls (font, size,
// colour, etc.) to show that element's current properties.
//
// When the user changes a toolbar control, it push those changes into the
// selected element.
//
// syncingControls flag: changing a control value programmatically triggers its
// "change" event, which would then try to update the element again — an infinite loop.
// Setting syncingControls = true while update the toolbar stops this.
// -------------------------------------------------------
function syncToolbarToElement(el) {
  if (el.type !== "text") return;
  syncingControls = true; // pause the "apply to element" listeners temporarily
  fontFamilySelect.value   = el.fontFamily || "Arial";
  textSizeInput.value      = el.fontSize;
  textColorInput.value     = el.color      || "#111111";
  textBgCheck.checked      = el.useBg      || false;
  textBgColor.value        = el.bgColor    || "#ffffff";
  boldToggle.classList.toggle("active", !!el.bold);
  italicToggle.classList.toggle("active", !!el.italic);
  syncingControls = false; // re-enable the listeners
}

// Reads the current toolbar values and pushes them into the selected element
function applyControlsToSelected() {
  if (syncingControls) return; // we're syncing the toolbar — don't loop
  const el = getSelected();
  if (!el || el.type !== "text") return;

  el.fontFamily = fontFamilySelect.value || "Arial";
  el.bold       = boldToggle.classList.contains("active");
  el.italic     = italicToggle.classList.contains("active");
  el.color      = textColorInput.value;
  el.useBg      = textBgCheck.checked;
  el.bgColor    = textBgColor.value;

  const newSize    = parseInt(textSizeInput.value || "48", 10);
  const maxAllowed = maxFontSizeForText(el); // don't let the text overflow the print area
  el.fontSize      = clamp(newSize, 10, maxAllowed);

  measureTextBox(el); // recalculate box size for the new font/size
  draw();
}

// Live update as the user types or picks — runs on every input event
[fontFamilySelect, textSizeInput, textColorInput, textBgColor].forEach(input => {
  input.addEventListener("input", applyControlsToSelected);
  // Push to undo history only when the user finishes changing the value
  input.addEventListener("change", () => { if (!syncingControls && getSelected()) pushHistory(); });
});

textBgCheck.addEventListener("change", () => {
  applyControlsToSelected();
  if (getSelected()) pushHistory();
});

boldToggle.addEventListener("click", () => {
  boldToggle.classList.toggle("active"); // toggles the "active" CSS class on/off
  applyControlsToSelected();
  if (getSelected()) pushHistory();
});

italicToggle.addEventListener("click", () => {
  italicToggle.classList.toggle("active");
  applyControlsToSelected();
  if (getSelected()) pushHistory();
});


// -------------------------------------------------------
// ADD TEXT
// Reads the text input and toolbar settings, creates a new text element,
// positions it in the centre of the print area, and adds it to the canvas.
// -------------------------------------------------------
addTextBtn.addEventListener("click", () => {
  const text = (textInput.value || "").trim();
  if (!text) return; // do nothing if the text box is empty

  const fontFamily = fontFamilySelect.value || "Arial";
  const bold       = boldToggle.classList.contains("active");
  const italic     = italicToggle.classList.contains("active");
  const useBg      = textBgCheck.checked;
  const bgColor    = textBgColor.value;
  const color      = textColorInput.value || "#111111";

  let fontSize  = parseInt(textSizeInput.value || "48", 10);
  const testEl  = { text, fontFamily, bold, italic, fontSize, color, useBg, bgColor };
  fontSize      = clamp(fontSize, 10, maxFontSizeForText(testEl)); // cap if too big

  const el = {
    id: crypto.randomUUID(), // unique ID so we can track which element is selected
    type: "text",
    text, fontSize, color, fontFamily, bold, italic, useBg, bgColor,
    opacity: 1,
    x: printArea.x + 10,
    y: printArea.y + 10,
    w: 200, h: 60,
  };

  measureTextBox(el);      // calculate the correct width/height for this text
  centreInPrintArea(el);   // move it to the middle of the print area

  selectedId = el.id;
  elements.push(el);
  syncOpacityUI();
  pushHistory();
  draw();
});


// -------------------------------------------------------
// UPLOAD IMAGE
// When the user picks an image file, read it as a data URL (base64 string)
// using FileReader, create an Image object from it, scale it to fit the print area,
// and add it to the canvas as an image element.
// -------------------------------------------------------
imageInput.addEventListener("change", (e) => {
  const file = e.target.files?.[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = () => {
    const img = new Image();
    img.onload = () => {
      // Scale the image down to fit within 90% of the print area, keeping aspect ratio
      const maxW  = printArea.w * 0.9;
      const maxH  = printArea.h * 0.9;
      const scale = Math.min(maxW / img.width, maxH / img.height, 1); // never scale up
      const w     = Math.max(MIN_BOX, Math.floor(img.width  * scale));
      const h     = Math.max(MIN_BOX, Math.floor(img.height * scale));

      const el = {
        id: crypto.randomUUID(),
        type: "image",
        img,       // the actual loaded Image object — used by ctx.drawImage()
        opacity: 1,
        x: printArea.x + 20, y: printArea.y + 20,
        w, h,
      };

      centreInPrintArea(el);
      selectedId = el.id;
      elements.push(el);
      syncOpacityUI();
      pushHistory();
      draw();
    };
    img.src = reader.result; // reader.result is the base64 data URL from FileReader
  };
  reader.readAsDataURL(file); // triggers reading the file; calls reader.onload when done
  e.target.value = ""; // reset so the same file can be uploaded again if needed
});


// -------------------------------------------------------
// MOUSE EVENTS — select, drag, resize
//
// On mousedown: check if the click hit an element's resize handle or body.
//   - Resize handle (bottom-right corner square) → start resizing
//   - Element body → select it and start dragging
//   - Empty space → deselect everything
//
// On mousemove: if dragging, move the element. If resizing, change its size.
//
// On mouseup: stop dragging/resizing. Push to undo history if something moved.
// -------------------------------------------------------
canvas.addEventListener("mousedown", (evt) => {
  const { x, y } = getMousePos(evt);
  didChange = false;

  // Check elements from top to bottom (last in array = on top visually)
  for (let i = elements.length - 1; i >= 0; i--) {
    const el = elements[i];

    // If this element is selected and click was on the resize handle
    if (el.id === selectedId && hitResizeHandle(el, x, y)) {
      isResizing = true;
      return;
    }

    // If click landed inside this element's bounding box
    if (hitTest(el, x, y)) {
      selectedId  = el.id;
      isDragging  = true;
      dragOffsetX = x - el.x; // how far from the element's left edge the click was
      dragOffsetY = y - el.y;
      syncOpacityUI();
      if (el.type === "text") syncToolbarToElement(el); // update toolbar for this text
      draw();
      return;
    }
  }

  // Click was on empty canvas — deselect
  selectedId = null;
  syncOpacityUI();
  draw();
});

canvas.addEventListener("mousemove", (evt) => {
  const el = getSelected();
  if (!el) return;

  const { x, y } = getMousePos(evt);

  if (isDragging) {
    // Move the element so the mouse stays at the same offset it was clicked
    el.x = x - dragOffsetX;
    el.y = y - dragOffsetY;
    clampToPrintArea(el); // keep within print area
    didChange = true;
    draw();
  }

  if (isResizing) {
    // Resize: set width/height based on how far the mouse is from the element's top-left
    const maxW = (printArea.x + printArea.w) - el.x; // can't go beyond the print area
    const maxH = (printArea.y + printArea.h) - el.y;
    el.w = clamp(x - el.x, MIN_BOX, maxW);
    el.h = clamp(y - el.y, MIN_BOX, maxH);

    // For text: scale the font size to match the new box height
    if (el.type === "text") {
      const maxAllowed = maxFontSizeForText(el);
      el.fontSize = clamp(Math.floor(el.h - TEXT_PAD * 2), 10, maxAllowed);
      measureTextBox(el);
    }

    clampToPrintArea(el);
    didChange = true;
    draw();
  }
});

window.addEventListener("mouseup", () => {
  // Only push history if the mouse actually moved (avoid undo steps for simple clicks)
  if (didChange) pushHistory();
  isDragging = false;
  isResizing = false;
  didChange  = false;
});


// -------------------------------------------------------
// ELEMENT CONTROL BUTTONS
// -------------------------------------------------------

// Delete the selected element
deleteBtn.addEventListener("click", () => {
  if (!selectedId) return;
  const idx = elements.findIndex(e => e.id === selectedId);
  if (idx >= 0) elements.splice(idx, 1); // remove from array
  selectedId = null;
  syncOpacityUI();
  pushHistory();
  draw();
});

// Duplicate: make a copy of the selected element, offset slightly so it's visible
duplicateBtn.addEventListener("click", () => {
  const el = getSelected();
  if (!el) return;
  const copy = { ...el, id: crypto.randomUUID(), x: el.x + 20, y: el.y + 20 };
  if (el.type === "image") copy.img = el.img; // share the Image object (it's read-only so this is safe)
  clampToPrintArea(copy);
  elements.push(copy);
  selectedId = copy.id;
  pushHistory();
  draw();
});

// Bring to front: move to end of array so it draws on top of everything else
bringFrontBtn.addEventListener("click", () => {
  if (!selectedId) return;
  const idx = elements.findIndex(e => e.id === selectedId);
  if (idx < 0) return;
  elements.push(elements.splice(idx, 1)[0]); // remove from current position, add at end
  pushHistory();
  draw();
});

// Send to back: move to start of array so it draws behind everything else
sendBackBtn.addEventListener("click", () => {
  if (!selectedId) return;
  const idx = elements.findIndex(e => e.id === selectedId);
  if (idx < 0) return;
  elements.unshift(elements.splice(idx, 1)[0]); // remove from current position, add at start
  pushHistory();
  draw();
});


// -------------------------------------------------------
// SAVE DESIGN
//
// When the user submits the save form, this runs before the form data is sent to Django.
// It:
//   1. Collects all element data into a JSON string (design_data)
//   2. Takes a screenshot of the canvas (canvas.toDataURL) as a base64 PNG
//   3. Checks if the screenshot is blank (Brave browser blocks canvas screenshots)
//   4. Populates the hidden form fields so Django receives them with the POST request
// -------------------------------------------------------
saveForm.addEventListener("submit", () => {
  sizeField.value = sizeSelect.value; // copy visible dropdown value to hidden field

  // Build the safe JSON representation of all elements
  // Image elements store their src URL (not the Image object, which can't be JSON-serialised)
  const safeElements = elements.map(el => ({
    id: el.id, type: el.type,
    x: el.x, y: el.y, w: el.w, h: el.h,
    opacity:    el.opacity  ?? 1,
    rotation:   el.rotation ?? 0,
    text:       el.type === "text"  ? el.text       : null,
    fontSize:   el.type === "text"  ? el.fontSize   : null,
    color:      el.type === "text"  ? el.color      : null,
    fontFamily: el.type === "text"  ? el.fontFamily : null,
    bold:       el.type === "text"  ? el.bold       : null,
    italic:     el.type === "text"  ? el.italic     : null,
    useBg:      el.type === "text"  ? el.useBg      : null,
    bgColor:    el.type === "text"  ? el.bgColor    : null,
    src:        el.type === "image" ? el.img?.src   : null,
  }));

  // Store the full design as JSON in the hidden form field
  designDataField.value = JSON.stringify({ printArea, shirtColor, elements: safeElements });

  // Deselect everything so the selection borders don't appear in the preview screenshot
  const prevSelected = selectedId;
  selectedId = null;
  draw();

  // Capture the canvas as a base64 PNG.
  // Brave's fingerprinting protection blocks toDataURL() on the visible canvas,
  // so we copy the pixels to a fresh offscreen canvas first — Brave does not block those.
  let dataUrl = "";
  try {
    const offscreen = document.createElement("canvas");
    offscreen.width  = canvas.width;
    offscreen.height = canvas.height;
    offscreen.getContext("2d").drawImage(canvas, 0, 0);
    dataUrl = offscreen.toDataURL("image/png");
    if (dataUrl === "data:,") dataUrl = ""; // blank result = still blocked
  } catch (err) {
    dataUrl = "";
  }

  // Final fallback: try the original canvas directly
  if (!dataUrl) {
    try { dataUrl = canvas.toDataURL("image/png"); } catch (_) { dataUrl = ""; }
  }

  previewField.value = dataUrl; // put the screenshot into the hidden field for Django
  selectedId = prevSelected;
  draw();
});

// Redraw when the browser restores this page from its back-forward cache (bfcache).
// The GPU canvas buffer is wiped when the page is cached, but our JS state survives.
// This event fires when the user presses Back and returns to this page.
window.addEventListener("pageshow", e => {
  if (e.persisted) draw();
});
