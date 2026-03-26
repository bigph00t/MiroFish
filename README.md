<div align="center">

<img src="./static/images/miromax_logo.png" alt="MiroMax Logo" width="75%"/>

[![GitHub Stars](https://img.shields.io/github/stars/bigph00t/MiroFish?style=flat-square&color=DAA520)](https://github.com/bigph00t/MiroFish/stargazers)
[![GitHub Forks](https://img.shields.io/github/forks/bigph00t/MiroFish?style=flat-square)](https://github.com/bigph00t/MiroFish/network)
[![Docker](https://img.shields.io/badge/Docker-Build-2496ED?style=flat-square&logo=docker&logoColor=white)](https://hub.docker.com/)

**MiroMax** - MiniMax-Optimized Multi-Agent Simulation Engine
</br>
<em>A Fork of MiroFish with Enhanced MiniMax API Support and Zep-Free Architecture</em>

[English](./README-EN.md) | [中文文档](./README.md)

</div>

## ⚡ Overview

**MiroMax** is an optimized fork of the MiroFish multi-agent simulation engine, specifically designed for:
- ✅ **MiniMax API Integration** - Native support for MiniMax LLM models
- ✅ **Zep-Free Architecture** - Runs entirely without Zep Cloud dependencies  
- ✅ **Multi-Model Support** - Use different MiniMax models for different agent types
- ✅ **Enhanced Stability** - Improved error handling and crash recovery
- ✅ **Date Seeding** - Better temporal context for simulations

## 🔧 Key Optimizations

### 1. MiniMax API Compatibility
- Removed `response_format` parameter (not supported by MiniMax)
- Enhanced JSON extraction and cleaning
- Auto-detection of MiniMax endpoints
- Support for M2.7, M2.5, M2.1, M2 models

### 2. Zep-Free Operation
- Local SQLite-based graph storage
- No cloud API dependencies
- Works offline after initial setup
- Simplified deployment

### 3. Multi-Model Configuration
```python
# Assign different models to different agent types
MINIMAX_MODELS = {
    "MiniMax-M2.7-highspeed": {"speed": "fast", "quality": "good"},
    "MiniMax-M2.7": {"speed": "medium", "quality": "better"},
    "MiniMax-Text-01": {"speed": "slow", "quality": "best"}
}
```

## 🚀 Quick Start

### Prerequisites
- Python 3.11-3.12
- Node.js 18+
- MiniMax API Key

### Installation

1. **Clone the repository:**
```bash
git clone https://github.com/bigph00t/MiroFish.git
cd MiroFish
```

2. **Configure environment:**
```bash
cp .env.example .env
# Edit .env and add your MiniMax API key:
# LLM_API_KEY=your_minimax_key
# LLM_BASE_URL=https://api.minimax.io/v1
# LLM_MODEL_NAME=MiniMax-M2.7-highspeed
```

3. **Install dependencies:**
```bash
npm run setup:all
```

4. **Start the application:**
```bash
npm run dev
```

## 📊 Usage Example

```bash
# Create a simulation
curl -X POST http://localhost:5001/api/simulation/create \
  -H 'Content-Type: application/json' \
  -d '{
    "project_id": "your_project",
    "enable_twitter": true,
    "enable_reddit": true
  }'

# Start the simulation
curl -X POST http://localhost:5001/api/simulation/start \
  -H 'Content-Type: application/json' \
  -d '{
    "simulation_id": "your_sim_id",
    "rounds": 144,
    "duration_hours": 336
  }'
```

## 🙏 Acknowledgments

This project is a fork of [MiroFish](https://github.com/666ghj/MiroFish) by 666ghj.

Original MiroFish is a project by Shanda Group, with the simulation engine powered by [OASIS](https://github.com/camel-ai/oasis) from CAMEL-AI.

## 📄 License

AGPL-3.0 License - See [LICENSE](./LICENSE) for details.
