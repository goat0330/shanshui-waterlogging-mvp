import { defineConfig } from "vite"
import { viteStaticCopy } from "vite-plugin-static-copy"

const cesiumSource = "node_modules/cesium/Build/Cesium"
const cesiumBaseUrl = "cesium"

export default defineConfig({
  plugins: [
    viteStaticCopy({
      targets: [
        { src: `${cesiumSource}/ThirdParty`, dest: cesiumBaseUrl, rename: { stripBase: 4 } },
        { src: `${cesiumSource}/Workers`, dest: cesiumBaseUrl, rename: { stripBase: 4 } },
        { src: `${cesiumSource}/Assets`, dest: cesiumBaseUrl, rename: { stripBase: 4 } },
        { src: `${cesiumSource}/Widgets`, dest: cesiumBaseUrl, rename: { stripBase: 4 } }
      ]
    })
  ],
  define: {
    CESIUM_BASE_URL: JSON.stringify(`/${cesiumBaseUrl}/`)
  },
  server: {
    host: "127.0.0.1",
    port: 4173,
    strictPort: true
  }
})
