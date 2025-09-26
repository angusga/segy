# 铯油田地面地下三维一体化（原型）

此项目是一个原型系统，用于在浏览器中通过 CesiumJS 展示油田地面/地下三维场景，并实现以下能力：
- 读取 SEGY 地震数据（后端解析元数据与切片）
- 实时查看钻头位置
- 实时钻井轨迹以三维管道（PolylineVolume）形式显示
- 为避开某些岩层提供基础数据对接能力（后续可接入层位/构造面）

本仓库包含：
- backend/：FastAPI 后端，负责 SEGY 解析和实时钻井数据的 WebSocket 推送
- frontend/：前端页面（CesiumJS），连接后端展示三维轨迹与钻头位置

## 快速启动

1) 后端（FastAPI）
- 创建虚拟环境并安装依赖

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
uvicorn backend.app:app --reload --host 0.0.0.0 --port 8000
```

2) 前端
- 直接用本地静态服务器（例如 `python -m http.server`）或者用 IDE 的静态文件服务打开 `frontend/index.html`。
- 默认 WebSocket 地址是 `ws://localhost:8000/ws/drill`，可在页面左上角修改。

## 功能说明

- SEGY 上传与解析
  - POST /api/segy/upload：上传 SEGY 文件（form-data: file），后端保存为 `backend/data/latest.sgy` 并返回元数据。
  - GET /api/segy/metadata：获取当前 SEGY 元数据（如 inline/xline 数量等）。
  - GET /api/segy/slice/inline/{iline} 和 /api/segy/slice/crossline/{xline}：返回归一化的二维切片数据（JSON）。可用于前端渲染层位或构造面提取的基础。

- 实时钻井数据
  - WebSocket /ws/drill：前端连接后可实时接收钻头与轨迹更新消息。
  - POST /api/drill/update：推送实时数据，示例请求体：
    ```json
    {
      "bit": [lon, lat, height],
      "md": 1234.5,
      "path": [[lon, lat, height], [lon, lat, height], ...]
    }
    ```
  - 前端会将轨迹以 PolylineVolume（可设置管径和颜色）显示为三维管道，并显示钻头位置。

## 说明与后续规划

- 目前后端使用 `segyio` 解析 SEGY 基本信息与切片，复杂的地下体（等值面、构造面、储层边界）建议在后端生成网格（glTF/3D Tiles）后由前端加载。
- CesiumJS 原生不支持体绘制（volume rendering），常用方案包括：
  - 体数据离散为多层切片（贴图）或等值面网格化为 glTF/3D Tiles。
  - 关键层位（需避开岩层）可做成矢量/网格模型并叠加显示，实现钻井路径与层位的空间关系判断。
- 实时数据可通过现场采集系统对接到 `/api/drill/update`，也可以扩展为 MQTT、Kafka 或数据库轮询。

## 目录结构

- backend/
  - app.py：FastAPI 应用与 WebSocket 推送
  - segy_processing.py：SEGY 上传与解析工具
  - requirements.txt：后端依赖
  - data/：上传的 SEGY 文件保存目录（运行时生成）

- frontend/
  - index.html：CesiumJS 页面
  - main.js：三维轨迹与钻头实体渲染逻辑

## 需要我继续完善什么？

- SEGY 到地层等值面/构造面的自动提取与三维网格化
- 钻井碰撞/避障逻辑（与已知层位实时判定）
- 实时数据的工业现场协议接入（MQTT/Kafka/OPC-UA）
- UI 增强与工程化前端框架（React/Vue）接入

如果你提供一份 SEGY 示例数据和现场钻井数据格式，我可以把解析与三维展示做成可直接演示的版本。