"""PWA metadata and install affordance for the Streamlit shell."""

from __future__ import annotations

import streamlit as st


def install_pwa_metadata() -> None:
    """Inject manifest/mobile metadata into the parent Streamlit document."""
    st.html(
        """
        <script>
        (() => {
          const host = window.parent;
          const doc = host.document;

          function ensureLink(rel, href, attrs = {}) {
            let node = doc.querySelector(`link[rel="${rel}"]`);
            if (!node) {
              node = doc.createElement("link");
              node.rel = rel;
              doc.head.appendChild(node);
            }
            node.href = href;
            Object.entries(attrs).forEach(([key, value]) => node.setAttribute(key, value));
          }

          function ensureMeta(name, content) {
            let node = doc.querySelector(`meta[name="${name}"]`);
            if (!node) {
              node = doc.createElement("meta");
              node.name = name;
              doc.head.appendChild(node);
            }
            node.content = content;
          }

          ensureLink("manifest", "/app/static/manifest.webmanifest");
          ensureLink("apple-touch-icon", "/app/static/icons/apple-touch-icon.png");
          ensureMeta("theme-color", "#19352a");
          ensureMeta("apple-mobile-web-app-capable", "yes");
          ensureMeta("apple-mobile-web-app-status-bar-style", "black-translucent");
          ensureMeta("apple-mobile-web-app-title", "NutriVision");
          ensureMeta("mobile-web-app-capable", "yes");

          doc.querySelectorAll(
            '.st-key-app-navigation [class*="st-key-nav-active-"] a'
          ).forEach((link) => link.setAttribute("aria-current", "page"));
          if (host.location.pathname === "/") {
            doc.querySelectorAll(
              ".st-key-app-brand [data-testid='stPageLink'] a, "
              + ".st-key-app-mobile-header [data-testid='stPageLink'] a"
            ).forEach((link) => link.setAttribute("aria-current", "page"));
          }

          if (!host.__nutriInstallListener) {
            host.__nutriInstallListener = true;
            host.addEventListener("beforeinstallprompt", (event) => {
              event.preventDefault();
              host.__nutriInstallPrompt = event;
            });
          }

          if ("serviceWorker" in host.navigator && !host.__nutriServiceWorkerRegistration) {
            host.__nutriServiceWorkerRegistration = host.navigator.serviceWorker
              .register("/app/static/service-worker.js", { scope: "/app/static/" })
              .catch(() => {
                host.__nutriServiceWorkerRegistration = null;
              });
          }
        })();
        </script>
        """,
        unsafe_allow_javascript=True,
    )


def render_install_button() -> None:
    """Render an install button with platform-specific manual fallback."""
    st.iframe(
        """
        <style>
          * { box-sizing: border-box; }
          body { margin: 0; font-family: Manrope, Arial, sans-serif; background: transparent; }
          .wrap { display: grid; grid-template-columns: auto 1fr; gap: 12px; align-items: center; }
          button {
            min-height: 46px; border: 0; border-radius: 14px; padding: 0 18px;
            background: #d9f45f; color: #19352a; font-weight: 800; cursor: pointer;
          }
          p { margin: 0; color: #687269; font-size: 12px; line-height: 1.4; }
          @media (max-width: 520px) {
            .wrap { grid-template-columns: 1fr; }
            button { width: 100%; }
          }
        </style>
        <div class="wrap">
          <button id="install">Cài NutriVision</button>
          <p id="hint">Mở nhanh như một ứng dụng, không cần tìm lại đường dẫn.</p>
        </div>
        <script>
          const button = document.getElementById("install");
          const hint = document.getElementById("hint");
          const host = window.parent;
          const installed = host.matchMedia("(display-mode: standalone)").matches
            || host.navigator.standalone === true;

          if (installed) {
            button.textContent = "Đã cài trên thiết bị";
            button.disabled = true;
            hint.textContent = "NutriVision đang chạy ở chế độ ứng dụng.";
          }

          const markInstalled = () => {
            button.textContent = "Đã cài trên thiết bị";
            button.disabled = true;
            hint.textContent = "Có thể mở NutriVision từ màn hình chính.";
          };
          host.addEventListener("appinstalled", markInstalled, { once: true });
          window.addEventListener("unload", () => {
            host.removeEventListener("appinstalled", markInstalled);
          });

          button.addEventListener("click", async () => {
            const prompt = host.__nutriInstallPrompt;
            if (prompt) {
              prompt.prompt();
              const result = await prompt.userChoice;
              if (result.outcome === "accepted") {
                button.textContent = "Đã thêm vào thiết bị";
                button.disabled = true;
              }
              host.__nutriInstallPrompt = null;
              return;
            }
            const isiOS = /iphone|ipad|ipod/i.test(host.navigator.userAgent)
              || (host.navigator.platform === "MacIntel" && host.navigator.maxTouchPoints > 1);
            hint.textContent = isiOS
              ? "Safari: nhấn Chia sẻ, sau đó chọn Thêm vào Màn hình chính."
              : "Mở menu trình duyệt và chọn Cài đặt ứng dụng, Thêm vào màn hình chính hoặc Thêm vào Dock.";
          });
        </script>
        """,
        height=86,
    )
