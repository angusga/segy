/* global Cesium */
(function () {
  const viewer = new Cesium.Viewer("cesiumContainer", {
    terrainProvider: Cesium.createWorldTerrain(),
    timeline: false,
    animation: false,
    baseLayerPicker: true,
    shadows: true,
    shouldAnimate: true,
  });

  const state = {
    ws: null,
    pathPositions: [], // Cesium.Cartesian3[]
    bitEntity: null,
    pipeEntity: null,
  };

  const statusEl = document.getElementById("status");
  const wsUrlEl = document.getElementById("wsUrl");
  const connectBtn = document.getElementById("connectBtn");
  const flyToBtn = document.getElementById("flyToBtn");
  const clearBtn = document.getElementById("clearBtn");
  const pipeDiameterEl = document.getElementById("pipeDiameter");
  const pipeColorEl = document.getElementById("pipeColor");

  connectBtn.addEventListener("click", connectWs);
  flyToBtn.addEventListener("click", () => {
    if (state.bitEntity) {
      viewer.flyTo(state.bitEntity, { duration: 1.5 });
    }
  });
  clearBtn.addEventListener("click", clearTrajectory);
  pipeDiameterEl.addEventListener("change", refreshPipe);
  pipeColorEl.addEventListener("change", refreshPipe);

  function connectWs() {
    try {
      if (state.ws) {
        state.ws.close();
        state.ws = null;
      }
      const url = wsUrlEl.value.trim();
      state.ws = new WebSocket(url);
      state.ws.onopen = () => {
        statusEl.textContent = "已连接";
      };
      state.ws.onmessage = (evt) => {
        const msg = JSON.parse(evt.data);
        if (msg.type === "drill_state") {
          applyDrillState(msg.payload);
        }
      };
      state.ws.onclose = () => {
        statusEl.textContent = "已断开";
      };
      state.ws.onerror = () => {
        statusEl.textContent = "连接错误";
      };
    } catch (e) {
      statusEl.textContent = "连接异常: " + e.message;
    }
  }

  function applyDrillState(payload) {
    const { bit, path } = payload || {};
    if (Array.isArray(path) && path.length) {
      state.pathPositions = path.map(([lon, lat, height]) => {
        return Cesium.Cartesian3.fromDegrees(lon, lat, height || 0);
      });
      refreshPipe();
    }

    if (Array.isArray(bit)) {
      const pos = Cesium.Cartesian3.fromDegrees(bit[0], bit[1], bit[2] || 0);
      if (!state.bitEntity) {
        state.bitEntity = viewer.entities.add({
          name: "钻头",
          position: pos,
          point: {
            pixelSize: 12,
            color: Cesium.Color.YELLOW,
            outlineColor: Cesium.Color.BLACK,
            outlineWidth: 1,
          },
          label: {
            text: "钻头",
            font: "14px sans-serif",
            style: Cesium.LabelStyle.FILL_AND_OUTLINE,
            outlineWidth: 2,
            verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
            pixelOffset: new Cesium.Cartesian2(0, -16),
          },
        });
      } else {
        state.bitEntity.position = pos;
      }
    }
  }

  function clearTrajectory() {
    if (state.pipeEntity) {
      viewer.entities.remove(state.pipeEntity);
      state.pipeEntity = null;
    }
    state.pathPositions = [];
  }

  function refreshPipe() {
    // Remove existing
    if (state.pipeEntity) {
      viewer.entities.remove(state.pipeEntity);
      state.pipeEntity = null;
    }
    if (!state.pathPositions || state.pathPositions.length < 2) return;

    const diameter = Math.max(0.05, parseFloat(pipeDiameterEl.value || "0.3"));
    const radius = diameter / 2.0;
    const circle = [];
    const segments = 32;
    for (let i = 0; i < segments; i++) {
      const angle = (i / segments) * Math.PI * 2;
      circle.push(new Cesium.Cartesian2(radius * Math.cos(angle), radius * Math.sin(angle)));
    }

    const colorHex = pipeColorEl.value || "#00ff66";
    const color = Cesium.Color.fromCssColorString(colorHex).withAlpha(0.95);

    state.pipeEntity = viewer.entities.add({
      name: "钻井管道",
      polylineVolume: {
        positions: state.pathPositions,
        shape: circle,
        material: color,
        outline: true,
        outlineColor: Cesium.Color.BLACK.withAlpha(0.4),
      },
    });

    // Fly to
    viewer.flyTo(state.pipeEntity, { duration: 1.2 });
  }

  // Initial camera view (placeholder location)
  viewer.camera.setView({
    destination: Cesium.Cartesian3.fromDegrees(50.0, 25.0, 5000.0),
    orientation: {
      heading: Cesium.Math.toRadians(0.0),
      pitch: Cesium.Math.toRadians(-30.0),
      roll: 0.0,
    },
  });
})();