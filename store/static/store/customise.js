// -------------------------
// Setup
// -------------------------
const canvas = document.getElementById("designerCanvas");
const ctx = canvas.getContext("2d");

const templateUrl = window.PRODUCT_TEMPLATE_URL;
const printArea = window.PRINT_AREA; // {x,y,w,h}

const addTextBtn = document.getElementById("addTextBtn");
const textInput = document.getElementById("textInput");
const textSizeInput = document.getElementById("textSize");
const textColorInput = document.getElementById("textColor");

const imageInput = document.getElementById("imageInput");

const deleteBtn = document.getElementById("deleteBtn");
const bringFrontBtn = document.getElementById("bringFrontBtn");

const saveForm = document.getElementById("saveForm");
const designDataField = document.getElementById("designData");
const previewField = document.getElementById("previewDataUrl");
const sizeSelect = document.getElementById("sizeSelect");
const sizeField = document.getElementById("sizeField");

// Elements on canvas
const elements = [];
let selectedId = null;

// Drag / resize state
let isDragging = false;
let isResizing = false;
let dragOffsetX = 0;
let dragOffsetY = 0;

// A little padding so text doesn't “touch” borders
const TEXT_PAD = 8;
const MIN_BOX = 30;

// Base template image (t-shirt)
const templateImg = new Image();
templateImg.src = templateUrl;

templateImg.onload = () => {
  draw();
};

// -------------------------
// Helpers
// -------------------------
function clamp(val, min, max) {
  return Math.max(min, Math.min(max, val));
}

function getMousePos(evt) {
  const rect = canvas.getBoundingClientRect();
  const scaleX = canvas.width / rect.width;
  const scaleY = canvas.height / rect.height;

  return {
    x: (evt.clientX - rect.left) * scaleX,
    y: (evt.clientY - rect.top) * scaleY,
  };
}

function getSelected() {
  return elements.find(e => e.id === selectedId) || null;
}

// keep an element fully inside print area
function clampToPrintArea(el) {
  el.x = clamp(el.x, printArea.x, printArea.x + printArea.w - el.w);
  el.y = clamp(el.y, printArea.y, printArea.y + printArea.h - el.h);
}

// checks if point is inside element box
function hitTest(el, x, y) {
  return x >= el.x && x <= el.x + el.w && y >= el.y && y <= el.y + el.h;
}

// resize handle = bottom-right corner square
function hitResizeHandle(el, x, y) {
  const size = 14;
  const hx = el.x + el.w - size;
  const hy = el.y + el.h - size;
  return x >= hx && x <= hx + size && y >= hy && y <= hy + size;
}

// Measure text properly (Django-level “realistic” sizing)
function measureTextBox(el) {
  ctx.save();
  ctx.font = `${el.fontSize}px Arial`;

  // Width is safe from measureText
  const metrics = ctx.measureText(el.text);
  const textW = metrics.width;

  // Height is trickier; use actual bounding box if available
  const ascent = metrics.actualBoundingBoxAscent ?? el.fontSize * 0.8;
  const descent = metrics.actualBoundingBoxDescent ?? el.fontSize * 0.2;
  const textH = ascent + descent;

  el.w = Math.max(60, Math.ceil(textW + TEXT_PAD * 2));
  el.h = Math.max(40, Math.ceil(textH + TEXT_PAD * 2));

  ctx.restore();

  // Keep it inside after measurement
  clampToPrintArea(el);
}

// Centres element in print area
function centreInPrintArea(el) {
  el.x = printArea.x + (printArea.w - el.w) / 2;
  el.y = printArea.y + (printArea.h - el.h) / 2;
  clampToPrintArea(el);
}

// Maximum font size that still fits print area width
function maxFontSizeForText(text) {
  // We do a quick search from big -> small
  const maxTry = 160;
  const minTry = 10;

  for (let size = maxTry; size >= minTry; size--) {
    ctx.save();
    ctx.font = `${size}px Arial`;
    const m = ctx.measureText(text);
    const w = m.width + TEXT_PAD * 2;

    const ascent = m.actualBoundingBoxAscent ?? size * 0.8;
    const descent = m.actualBoundingBoxDescent ?? size * 0.2;
    const h = (ascent + descent) + TEXT_PAD * 2;

    ctx.restore();

    if (w <= printArea.w && h <= printArea.h) return size;
  }

  return minTry;
}

// -------------------------
// Drawing
// -------------------------
function drawPrintArea() {
  ctx.save();
  ctx.setLineDash([8, 6]);
  ctx.strokeStyle = "#2b67ff";
  ctx.lineWidth = 2;
  ctx.strokeRect(printArea.x, printArea.y, printArea.w, printArea.h);
  ctx.restore();
}

function drawElement(el) {
  // element border if selected
  if (el.id === selectedId) {
    ctx.save();
    ctx.strokeStyle = "#2563eb";
    ctx.lineWidth = 2;
    ctx.strokeRect(el.x, el.y, el.w, el.h);

    // resize handle
    ctx.fillStyle = "#2563eb";
    ctx.fillRect(el.x + el.w - 14, el.y + el.h - 14, 14, 14);
    ctx.restore();
  }

  if (el.type === "text") {
    ctx.save();
    ctx.font = `${el.fontSize}px Arial`;
    ctx.fillStyle = el.color;
    ctx.textBaseline = "top";

    // Draw text with padding inside its box
    ctx.fillText(el.text, el.x + TEXT_PAD, el.y + TEXT_PAD);
    ctx.restore();
  }

  if (el.type === "image" && el.img) {
    ctx.drawImage(el.img, el.x, el.y, el.w, el.h);
  }
}

function draw() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  // background (template image)
  ctx.drawImage(templateImg, 0, 0, canvas.width, canvas.height);

  // print area guide
  drawPrintArea();

  // elements (in order)
  for (const el of elements) {
    drawElement(el);
  }
}

// -------------------------
// Add Text
// -------------------------
addTextBtn.addEventListener("click", () => {
  const text = (textInput.value || "").trim();
  if (!text) return;

  let fontSize = parseInt(textSizeInput.value || "48", 10);
  const color = textColorInput.value || "#111111";

  // Hard limit font size so user can't instantly overflow
  const maxAllowed = maxFontSizeForText(text);
  fontSize = clamp(fontSize, 10, maxAllowed);

  const el = {
    id: crypto.randomUUID(),
    type: "text",
    text,
    fontSize,
    color,
    x: printArea.x + 10,
    y: printArea.y + 10,
    w: 200,
    h: 60,
  };

  // Measure properly, then centre inside print area
  measureTextBox(el);
  centreInPrintArea(el);

  selectedId = el.id;
  elements.push(el);
  draw();
});

// -------------------------
// Upload Image
// -------------------------
imageInput.addEventListener("change", (e) => {
  const file = e.target.files?.[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = () => {
    const img = new Image();
    img.onload = () => {
      // Start size: fit nicely inside print area
      const maxW = printArea.w * 0.9;
      const maxH = printArea.h * 0.9;

      // keep aspect ratio
      let w = img.width;
      let h = img.height;
      const scale = Math.min(maxW / w, maxH / h, 1);
      w = Math.max(MIN_BOX, Math.floor(w * scale));
      h = Math.max(MIN_BOX, Math.floor(h * scale));

      const el = {
        id: crypto.randomUUID(),
        type: "image",
        img,
        x: printArea.x + 20,
        y: printArea.y + 20,
        w,
        h,
      };

      centreInPrintArea(el);

      selectedId = el.id;
      elements.push(el);
      draw();
    };
    img.src = reader.result;
  };
  reader.readAsDataURL(file);

  // reset input so uploading same file again still triggers change
  e.target.value = "";
});

// -------------------------
// Mouse interactions (drag + resize)
// -------------------------
canvas.addEventListener("mousedown", (evt) => {
  const { x, y } = getMousePos(evt);

  for (let i = elements.length - 1; i >= 0; i--) {
    const el = elements[i];

    // Resize handle only works on selected element
    if (el.id === selectedId && hitResizeHandle(el, x, y)) {
      isResizing = true;
      return;
    }

    if (hitTest(el, x, y)) {
      selectedId = el.id;

      isDragging = true;
      dragOffsetX = x - el.x;
      dragOffsetY = y - el.y;

      draw();
      return;
    }
  }

  selectedId = null;
  draw();
});

canvas.addEventListener("mousemove", (evt) => {
  const el = getSelected();
  if (!el) return;

  const { x, y } = getMousePos(evt);

  if (isDragging) {
    el.x = x - dragOffsetX;
    el.y = y - dragOffsetY;

    clampToPrintArea(el);
    draw();
  }

  if (isResizing) {
    // Resize from bottom-right, but stop at print area edges
    const maxW = (printArea.x + printArea.w) - el.x;
    const maxH = (printArea.y + printArea.h) - el.y;

    el.w = clamp(x - el.x, MIN_BOX, maxW);
    el.h = clamp(y - el.y, MIN_BOX, maxH);

    // If text: resizing tries to change font size, but must still fit
    if (el.type === "text") {
      const targetFont = clamp(Math.floor(el.h - TEXT_PAD * 2), 10, 200);

      // also respect max font for that specific text
      const maxAllowed = maxFontSizeForText(el.text);
      el.fontSize = clamp(targetFont, 10, maxAllowed);

      measureTextBox(el);
    }

    clampToPrintArea(el);
    draw();
  }
});

window.addEventListener("mouseup", () => {
  isDragging = false;
  isResizing = false;
});

// -------------------------
// Buttons: delete / bring to front
// -------------------------
deleteBtn.addEventListener("click", () => {
  if (!selectedId) return;
  const idx = elements.findIndex(e => e.id === selectedId);
  if (idx >= 0) elements.splice(idx, 1);
  selectedId = null;
  draw();
});

bringFrontBtn.addEventListener("click", () => {
  if (!selectedId) return;
  const idx = elements.findIndex(e => e.id === selectedId);
  if (idx < 0) return;

  const [picked] = elements.splice(idx, 1);
  elements.push(picked);
  draw();
});

// -------------------------
// Save design (JSON + preview PNG)
// -------------------------
saveForm.addEventListener("submit", () => {
  sizeField.value = sizeSelect.value;

  const safeElements = elements.map(e => ({
    id: e.id,
    type: e.type,
    x: e.x, y: e.y, w: e.w, h: e.h,
    text: e.type === "text" ? e.text : null,
    fontSize: e.type === "text" ? e.fontSize : null,
    color: e.type === "text" ? e.color : null,
    src: e.type === "image" ? e.img.src : null,
  }));

  designDataField.value = JSON.stringify({
    printArea,
    elements: safeElements,
  });

  previewField.value = canvas.toDataURL("image/png");
});
