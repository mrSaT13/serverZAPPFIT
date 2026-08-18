/**
 * Docs helper for generating secrets equivalent to OpenSSL commands.
 *
 * @returns {void}
 * @throws {Error} Never throws intentionally.
 */
function initializeSecretTools() {
  const toolContainers = document.querySelectorAll("[data-secret-tools]");
  if (toolContainers.length === 0) {
    return;
  }

  toolContainers.forEach((container) => {
    const tools = container.querySelectorAll("[data-secret-tool]");
    tools.forEach((tool) => {
      if (tool.getAttribute("data-secret-initialized") === "true") {
        return;
      }

      const format = tool.getAttribute("data-format");
      const bytes = Number(tool.getAttribute("data-bytes") || "32");
      const output = tool.querySelector(".secret-tools__output");
      const status = tool.querySelector("[data-secret-status]");
      const generateButton = tool.querySelector("[data-secret-generate]");
      const copyButton = tool.querySelector("[data-secret-copy]");

      if (!(output instanceof HTMLInputElement) || !status || !generateButton || !copyButton) {
        return;
      }

      generateButton.addEventListener("click", () => {
        const value = generateSecret(format, bytes);
        if (!value) {
          status.textContent = "Unable to generate secret on this browser.";
          return;
        }

        output.value = value;
        status.textContent = "Secret generated.";
      });

      copyButton.addEventListener("click", async () => {
        if (!output.value) {
          status.textContent = "Generate a value first.";
          return;
        }

        const copied = await copyText(output.value);
        status.textContent = copied ? "Copied to clipboard." : "Clipboard copy failed.";
      });

      tool.setAttribute("data-secret-initialized", "true");
    });
  });
}

/**
 * Generates a random secret using cryptographically secure random bytes.
 *
 * @param {string | null} format - Output format: "hex" or "base64".
 * @param {number} bytes - Number of random bytes to generate.
 * @returns {string}
 * @throws {Error} Never throws intentionally.
 */
function generateSecret(format, bytes) {
  if (!window.crypto || typeof window.crypto.getRandomValues !== "function") {
    return "";
  }

  const randomBytes = new Uint8Array(bytes);
  window.crypto.getRandomValues(randomBytes);

  if (format === "hex") {
    return Array.from(randomBytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
  }

  if (format === "base64") {
    let binary = "";
    randomBytes.forEach((byte) => {
      binary += String.fromCharCode(byte);
    });

    return window.btoa(binary);
  }

  return "";
}

/**
 * Copies text to clipboard with a fallback for older browsers.
 *
 * @param {string} text - Text to copy.
 * @returns {Promise<boolean>}
 * @throws {Error} Never throws intentionally.
 */
async function copyText(text) {
  if (navigator.clipboard && typeof navigator.clipboard.writeText === "function") {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch (_error) {
      // Fallback is attempted below.
    }
  }

  const fallbackInput = document.createElement("textarea");
  fallbackInput.value = text;
  fallbackInput.setAttribute("readonly", "");
  fallbackInput.style.position = "absolute";
  fallbackInput.style.left = "-9999px";
  document.body.appendChild(fallbackInput);
  fallbackInput.select();

  let copied = false;
  try {
    copied = document.execCommand("copy");
  } catch (_error) {
    copied = false;
  }

  document.body.removeChild(fallbackInput);
  return copied;
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initializeSecretTools);
} else {
  initializeSecretTools();
}