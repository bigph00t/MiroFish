# MiroMax - Changes from MiroFish

## Overview
MiroMax is an optimized fork of MiroFish specifically designed for MiniMax API integration and Zep-free operation.

## Key Changes

### 1. LLMClient Optimization (`backend/app/utils/llm_client.py`)
**Problem**: MiniMax API doesn't support `response_format` parameter
**Solution**: 
- Added MiniMax detection: `is_minimax = "minimax" in self.base_url.lower()`
- Only add `response_format` for non-MiniMax providers
- Enhanced `<thinking>` tag cleaning for MiniMax M2.5+

### 2. Config Validation (`backend/app/config.py`)
**Problem**: ZEP_API_KEY was required even for local graph operation
**Solution**:
- Commented out ZEP_API_KEY validation
- Made ZEP optional - system now uses local graph engine

### 3. API Endpoints (`backend/app/api/graph.py`, `backend/app/api/simulation.py`)
**Problem**: Multiple endpoints checked for ZEP_API_KEY and failed if missing
**Solution**:
- Commented out ZEP key checks
- Updated error messages
- Changed builder initialization to not require API key

### 4. Profile Structure (`backend/zep_cloud_local_shim/types.py`)
**Problem**: OASIS library expects flat profile structure with mbti, gender, age at top level
**Solution**:
- Added `processed` field to Episode dataclass
- Added `labels` property to Node class
- Added `name` property to Edge class
- Ensured profiles have flat structure: `mbti`, `gender`, `age`, `country`

### 5. Simulation Config Generator (`backend/app/services/simulation_config_generator.py`)
**Problem**: Uses `response_format` which MiniMax doesn't support
**Solution**:
- Removed `response_format={"type": "json_object"}` from LLM calls
- Added explicit JSON instructions to system prompts instead

## Files Modified

### Core Changes
1. `backend/app/utils/llm_client.py` - MiniMax compatibility
2. `backend/app/config.py` - Optional ZEP
3. `backend/app/api/graph.py` - Remove ZEP checks
4. `backend/app/api/simulation.py` - Remove ZEP checks
5. `backend/app/services/simulation_config_generator.py` - No response_format

### Shim Updates
6. `backend/zep_cloud_local_shim/types.py` - Profile structure fixes
7. `backend/zep_cloud_local_shim/store.py` - Already compatible

### Shadow Modules (for imports)
8. `backend/zep_cloud/__init__.py` - Redirects to local shim
9. `backend/zep_cloud/client.py` - Shadow module
10. `backend/zep_cloud/external_clients/__init__.py` - Shadow module
11. `backend/zep_cloud/external_clients/ontology.py` - Shadow module

## Testing

Successfully tested with:
- Simulation: sim_7f5351c0c527
- Duration: 336 rounds (18 months simulated)
- Agents: 181
- Actions: 6,794 total
- Platforms: Twitter (5,705), Reddit (1,089)
- Runtime: ~1.5 hours
- Status: ✅ COMPLETE

## Requirements

### API Keys
- **Required**: MiniMax API Key
- **Optional**: Zep Cloud Key (not needed)

### Environment Variables
```bash
# MiniMax Configuration (REQUIRED)
LLM_API_KEY=your_minimax_key
LLM_BASE_URL=https://api.minimax.io/v1
LLM_MODEL_NAME=MiniMax-M2.7-highspeed

# MiniMax for Boost (same credentials)
LLM_BOOST_API_KEY=your_minimax_key
LLM_BOOST_BASE_URL=https://api.minimax.io/v1
LLM_BOOST_MODEL_NAME=MiniMax-M2.7-highspeed

# Zep Cloud (OPTIONAL - not needed)
# ZEP_API_KEY=your_zep_key
```

## Future Enhancements

### Multi-Model Support
```python
# TODO: Implement per-agent model selection
MODEL_ASSIGNMENTS = {
    "analysts": "MiniMax-M2.7-highspeed",
    "executives": "MiniMax-M2.7",
    "traders": "MiniMax-Text-01"
}
```

### Date Seeding
```python
# TODO: Add simulation date context
simulation_start_date = "2026-03-26"
current_date = "2026-03-26"
```

---

**MiroMax**: Optimized for MiniMax, Free from Zep dependencies
