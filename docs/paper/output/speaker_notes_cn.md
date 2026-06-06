# 中文讲者提示

## Slide 1. PyISIS: 基于 ISIS 的行星遥感制图开发库
- Python 直连 ISIS 几何核心
- 面向自动控制网与深度匹配工作流
- Xun Geng · 2026

## Slide 2. 瓶颈不是单个算法，而是 ISIS 与 Python 工作流断裂
- ISIS 几何严谨，但以 C++/命令行为主
- Python 生态适合算法研发与深度匹配
- 中间文件与 subprocess 限制迭代效率
- 光照变化与弱纹理使固定匹配器失效

## Slide 3. PyISIS 的核心定位：把摄影测量 API 带进 Python
- 暴露 200+ ISIS C++ 类与类型
- 覆盖 50+ 任务相机、SPICE、投影、控制网与束平差配置
- 贡献是可复用开发库，而非新特征匹配器

## Slide 4. 五层架构让 ISIS 几何与科学 Python 生态共存
- pybind11 薄绑定保留 C++ 语义
- 七个 Python 模块组织核心能力
- 应用层支持匹配、控制网与 bundle adjustment

## Slide 5. 端到端流程从 ISIS Cube 走到 jigsaw 可用控制网
- DOM 匹配后回投到原始 line/sample
- ControlPoint / ControlMeasure 由 Python 直接构建

## Slide 6. 自适应路由用物理几何信号选择匹配策略
- 纹理稀疏度 S：SIFT 密度、梯度、GLCM
- 光照差异 D：SPICE 太阳高度角与方位角
- 质量门控失败后级联升级

## Slide 7. 路由规则把匹配选择变成可审计决策
- S≤0.35 且 D≤0.20：优先 SIFT/FLANN
- S≥0.65 或 D≥0.55：优先 LoFTR
- 中间区域使用 LightGlue

## Slide 8. 六对 LRO NAC 影像全部生成控制网
- 总计 121,856 个控制点
- 212,972 个候选匹配经 RANSAC 过滤
- 约 19% tile 被有效像素预筛剔除

## Slide 9. 同轨道落在 SIFT 区，跨轨影像进入深度匹配区
- 决策边界：S=0.35/0.65，D=0.20/0.55
- Pair 5 弱纹理，Pair 6 大方位角差
- 路由解释了为什么不能固定单一方法

## Slide 10. 自适应策略保持 3/3 成功，同时减少深度模型任务
- adaptive: 15 个 deep tile tasks
- 固定深度匹配器：各 27 个 tasks
- 深度任务减少 44.4%，仍满足 10 点成功准则

## Slide 11. 匹配线矩阵显示：自适应追求足够且稳定的控制点
- 稀疏纹理对：adaptive 208 点，高于 SIFT+FLANN 67 点
- 富纹理对：adaptive 10,415 点，避免全局深度匹配
- 中等纹理对：adaptive 1,985 点，接近 SIFT+LightGlue

## Slide 12. 绑定层几何精度保持在亚毫像素量级
- DOM→原图回投开销仅 1.03–1.10×
- 最大往返误差 0.278×10⁻³ pixels
- 成功率 99.9990–99.9998%

## Slide 13. 太阳几何与 ControlNet 遍历验证了库级可用性
- 太阳角计算开销 1.02–1.05×
- 太阳方位/高度误差显示为 0.000×10⁻³ degrees
- 84.2 MB 控制网遍历 462,222 measures 用时 7.01 s

## Slide 14. 结论：PyISIS 是行星制图算法研发的 Python 化底座
- 直接 API 访问减少文件耦合
- SPICE-aware 路由适配月球弱纹理与强光照差
- 当前验证仍局限于 6 对 LRO NAC
- 下一步：findfeatures / AutoCNet / jigsaw 残差验证
