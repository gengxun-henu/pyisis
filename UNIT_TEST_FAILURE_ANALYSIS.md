# 单元测试失败分析报告

## 问题概述

在发布版本环境中运行单元测试时，出现 12 个测试失败（11 个 ERROR，1 个 FAIL），全部与序列号（SerialNumber）生成相关。

## 根本原因

**所有失败都源于同一问题：ISISDATA 环境变量未正确配置**

ISIS SerialNumber.compose() 需要从 `$ISISDATA/base/translations/` 或 `$ISISROOT/appdata/translations/` 读取翻译文件来从 cube 标签中提取序列号。对于 Messenger MDIS-NAC cube，需要以下翻译文件：

1. `MissionName2DataDir.trn` - 将任务名称映射到数据目录
2. `Instruments.trn` - 仪器名称映射
3. `MessengerMDIS-NACSerialNumber.trn` （或类似名称）- Messenger MDIS-NAC 专用序列号翻译

## 当前状况

- 测试 cube 文件：`tests/data/mosrange/EN0108828322M_iof.cub` （Messenger MDIS-NAC）
- ISISDATA mockup 位置：`tests/data/isisdata/mockup/`
- **问题**：mockup 只包含 hayabusa、smart1、voyager1 任务的数据，**缺少 Messenger 支持**

## 为什么开发环境可以工作

开发环境中：
- conda `asp360_new` 环境已安装完整的 ISIS
- `$ISISDATA` 指向完整的翻译文件集
- 所有必需的 Messenger 翻译文件都存在

## 为什么发布环境失败

发布/测试环境中：
- `$ISISDATA` 未设置或设置不正确
- ISISDATA mockup 不完整
- SerialNumber.compose() 找不到翻译文件，返回 "Unknown"

## 失败的测试列表

### serial_number_unit_test.py (4个)
1. `test_serial_and_observation_compose_from_filename_and_cube` - FAIL
2. `test_serial_number_list_single_file_round_trip` - ERROR
3. `test_observation_lookup_and_compose_observation` - ERROR
4. `test_remove_updates_membership` - ERROR

### control_core_unit_test.py (8个)
1. `test_control_net_filter_cube_name_expression_filter_keeps_matching_serials` - ERROR
2. `test_control_net_filter_cube_num_points_filter_keeps_expected_images` - ERROR
3. `test_control_net_filter_cube_stats_header_writes_expected_text` - ERROR
4. `test_control_net_filter_output_helpers_write_expected_text` - ERROR
5. `test_control_net_filter_point_edit_lock_filter_keeps_matching_points` - ERROR
6. `test_control_net_filter_point_id_filter_keeps_matching_points` - ERROR
7. `test_control_net_filter_point_measures_filter_keeps_expected_points` - ERROR
8. `test_control_net_filter_point_properties_filter_keeps_fixed_points` - ERROR

## 解决方案

### 方案 1：使用系统 ISISDATA（推荐用于您的环境）

确保激活正确的 conda 环境并设置 ISISDATA：

```bash
# 激活 asp360_new 环境
conda activate asp360_new

# 验证环境变量
echo $ISISDATA
echo $ISIS_PREFIX

# 如果 ISISDATA 未设置，手动设置（根据您的 ISIS 安装路径）
export ISISDATA=/path/to/your/isis/data

# 运行测试
python -m unittest discover -s tests/unitTest -p "*_unit_test.py"
```

### 方案 2：扩展 ISISDATA mockup（用于 CI/可移植测试）

向 `tests/data/isisdata/mockup/` 添加 Messenger 翻译文件。需要：

1. 创建 `tests/data/isisdata/mockup/base/translations/` 目录
2. 添加核心翻译文件：
   - `MissionName2DataDir.trn`
   - `Instruments.trn`
3. 创建 `tests/data/isisdata/mockup/messenger/` 目录
4. 添加 Messenger 专用翻译：
   - `translations/MessengerMDIS-NACSerialNumber.trn`
   - `translations/MessengerMDIS-WACSerialNumber.trn`

这些文件需要从完整的 ISIS 安装中复制。

### 方案 3：使用不同的测试 cube（临时解决方案）

将测试修改为使用 mockup 中已支持的任务（hayabusa、smart1、voyager1）的 cube 文件。这不是理想方案，因为会改变测试覆盖范围。

## 验证步骤

设置 ISISDATA 后，可以快速验证：

```python
import os
os.environ['ISISDATA'] = '/path/to/isisdata'  # 或使用 mockup 路径

import isis_pybind as ip

# 测试序列号生成
cube_path = 'tests/data/mosrange/EN0108828322M_iof.cub'
serial = ip.SerialNumber.compose(cube_path)
print(f"Serial number: {serial}")  # 应该不是 "Unknown"
```

## 推荐行动

1. **立即行动**：激活 `asp360_new` conda 环境并确保 ISISDATA 正确设置
2. **长期方案**：
   - 如果需要 CI 或可移植测试，扩展 ISISDATA mockup
   - 或者创建测试环境设置脚本，自动配置 ISISDATA
   - 或者在 `_unit_test_support.py` 中添加更好的环境检查和错误消息

## 技术细节

错误消息示例：
```
isis_pybind._isis_core.IException: **USER ERROR** Invalid serial number [Unknown]
from file [/home/gengxun/PlanetaryMapping/pyisis/pyisis-1.0.0/tests/data/mosrange/EN0108828322M_iof.cub].
```

这表明：
- Cube 文件本身是有效的
- Instrument 组包含所需字段（SpacecraftName=Messenger, InstrumentId=MDIS-NAC）
- 但翻译文件缺失，导致无法生成序列号
