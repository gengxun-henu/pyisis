User: 另外，深度学习特征提取算法，比如ＳＵＰＥＲＰＯＩＮＴ，ＤＩＳＫ，ＬＯＦＴＲ等是不是有些适用于月球的弱纹理，或者大的光照差异的，而一些纹理丰富的与光照差异小的适合ＳＩＦＴ特征提取？就是从特征提取与匹配两个维度说一下经典ＳＩＦＴ以及常用深度学习匹配优点

GitHub Copilot: 是的，你这个判断方向基本正确：**纹理丰富、光照差异小的影像对，经典 SIFT 往往很稳、成本低、可解释；弱纹理、大光照差异、低重复纹理或视角变化更复杂的场景，SuperPoint / DISK / LoFTR / SuperGlue / LightGlue 这类深度方法更有机会胜出**。但要注意一点：深度学习方法是否适合月球影像，不只看算法名，还强烈依赖它的训练数据、域泛化能力和后处理质量门控。

下面从 **特征提取** 和 **特征匹配** 两个维度展开。

## 一句话结论

对于月球 DOM / 轨道影像匹配，可以粗略这样理解：

| 场景 | 更适合的方法 |
|---|---|
| 纹理丰富、尺度/旋转变化中等、光照差异小 | SIFT / RootSIFT + RANSAC |
| 局部纹理较少，但仍有角点、边缘、陨石坑结构 | SuperPoint / DISK + LightGlue / SuperGlue |
| 弱纹理、大面积平滑、重复坑洼、局部特征很少 | LoFTR / ASpanFormer / DKM 类 detector-free 方法 |
| 大光照差异、阴影方向变化明显 | 深度方法可能更好，但仍需质量门控；必要时结合渲染 probe / shadow mask |
| 地形阴影主导、太阳高度差极大 | 单纯特征匹配都可能不稳，最好加光照感知路由、DEM render probe、残差门控 |

所以你当前 adaptive routing 的思路是对的：**不要固定一种 matcher，而是根据 pair 的纹理、光照和质量反馈选择 SIFT / SuperPoint / DISK / LoFTR 等路径。**

---

## 1. 特征提取维度

### 1.1 SIFT：经典、稳定、可解释，但依赖可见局部纹理

SIFT 的核心是检测尺度空间 extrema，然后用局部梯度方向直方图构造描述子。它的优点非常明显：

- 对尺度变化有较好鲁棒性；
- 对旋转变化有较好鲁棒性；
- 对普通亮度/对比度变化有一定鲁棒性；
- 不需要训练数据；
- 可解释、调参简单；
- 运行成本较低；
- 和 RANSAC / 几何约束结合成熟。

对于月球影像，如果两幅图：

- 分辨率接近；
- 太阳高度角差异不大；
- 阴影方向差异不大；
- 表面有明显陨石坑、岩块、边缘、纹理；
- DOM 间几何关系近似平面或可以用局部模型解释；

那么 SIFT 往往非常可靠。

但 SIFT 的弱点也很典型：

- 对大面积弱纹理区域提不出足够稳定点；
- 对强阴影变化敏感；
- 对非线性光照变化、太阳相位角变化、阴影边界移动不鲁棒；
- 对低对比、过曝、暗区、压缩噪声比较敏感；
- 它只看局部梯度，不理解更大范围的结构。

月球影像里一个典型问题是：**很多“纹理”其实是光照造成的阴影纹理，而不是稳定的物理纹理**。太阳角度一变，阴影边界就移动，SIFT 可能把阴影边界当成稳定特征，导致误匹配。

因此，SIFT 更适合：

> 纹理清楚、光照接近、阴影变化不剧烈、局部结构稳定的影像对。

---

### 1.2 SuperPoint：学习式关键点 + 描述子，适合比 SIFT 更复杂的局部纹理

SuperPoint 是一种学习式局部特征方法，既检测关键点，也生成描述子。相比 SIFT，它的优势是：

- 特征点检测更“语义化”一些；
- 在低纹理区域可能比 SIFT 找到更稳定的点；
- 描述子对某些光照、模糊、噪声变化更鲁棒；
- 和 SuperGlue / LightGlue 搭配时效果通常明显优于传统最近邻匹配。

但 SuperPoint 也不是魔法棒。它原始训练常来自自然图像或合成几何数据，面对月球影像时可能出现 domain gap：

- 月表纹理和自然图像差异大；
- 阴影形态强烈受太阳角控制；
- 大量灰度、低纹理、重复坑形结构可能让关键点不稳定；
- 如果未针对遥感/月球数据微调，泛化能力不一定稳定。

所以 SuperPoint 更适合：

> 有一定结构但 SIFT 不够稳定的影像，例如低对比陨石坑边缘、轻微光照差异、轻微模糊或尺度变化。

---

### 1.3 DISK：学习式特征，通常比 SuperPoint 更偏向端到端匹配质量

DISK 也是学习式局部特征。相比 SuperPoint，DISK 更强调通过奖励机制学习“容易匹配、匹配后几何一致”的点。它的特点是：

- 对可匹配性有更直接的优化目标；
- 在某些复杂视角和光照变化下可能比 SIFT / SuperPoint 更稳；
- 适合和 LightGlue 等现代 matcher 配合；
- 对弱纹理和低对比区域有时更有优势。

但它也有类似问题：

- 是否适合月球影像取决于训练域；
- 对极端阴影变化仍可能失败；
- 可能产生置信度高但几何错误的匹配，需要 RANSAC/残差门控。

DISK 更适合：

> 局部纹理不是特别丰富、但仍有可学习结构的场景，例如陨石坑边缘、沟槽、山脊、撞击坑链等。

---

### 1.4 LoFTR：不是传统“先提点再匹配”，而是 detector-free 匹配

LoFTR 很关键，因为它和 SIFT / SuperPoint / DISK 的逻辑不同。

SIFT、SuperPoint、DISK 基本是：

> 先提关键点和描述子，再做匹配。

LoFTR 是：

> 不显式依赖关键点检测，而是通过 transformer 在图像间建立稠密或半稠密对应关系。

这使得 LoFTR 对一些弱纹理场景很有优势：

- 当关键点检测器找不到足够点时，LoFTR 仍可能建立匹配；
- 利用较大上下文，不只看局部 patch；
- 对重复纹理、低纹理区域可能比 sparse keypoint 方法更好；
- 对宽基线和视角变化有一定优势。

对月球弱纹理场景，LoFTR 是非常值得尝试的，尤其是：

- 大面积灰度变化平缓；
- SIFT 点数不足；
- SuperPoint / DISK 匹配稀疏；
- 需要更密集的对应点；
- 图像间有较明显几何变形但仍可由局部连续变换解释。

但 LoFTR 也有明显代价：

- 计算成本高；
- 显存需求高；
- 对输入分辨率敏感；
- 对大光照变化不一定稳定；
- 如果两幅图的阴影结构完全变了，也可能匹配到“光照形状”而不是地形本体；
- 对月球数据未微调时可能有 domain gap。

所以 LoFTR 更适合：

> 弱纹理、SIFT 点数不足、需要稠密上下文匹配的影像对，但必须配合严格几何验证。

---

## 2. 特征匹配维度

除了“提什么特征”，还要看“怎么匹配”。这两层要分开。

### 2.1 传统匹配：最近邻 + ratio test + RANSAC

SIFT 常用流程是：

1. 提取 SIFT keypoints；
2. 计算 SIFT descriptors；
3. 最近邻匹配；
4. Lowe ratio test；
5. cross-check 可选；
6. RANSAC 估计 homography / affine / fundamental / local transform；
7. 过滤 outliers。

优点：

- 简单稳定；
- 可解释；
- 速度快；
- 工程成熟；
- 对纹理丰富场景非常好用。

缺点：

- 匹配只基于局部描述子距离；
- 不充分利用全局上下文；
- 重复结构容易误匹配；
- 弱纹理下点数不足；
- 大光照差异时描述子距离可能失真。

所以传统匹配适合：

> 纹理丰富、重复结构少、光照接近、几何变换温和的场景。

---

### 2.2 SuperGlue：图神经网络匹配，适合 sparse feature 的上下文筛选

SuperGlue 通常搭配 SuperPoint，也可搭配其他局部特征。它的优势是：

- 不只是看描述子距离，还看点集之间的上下文关系；
- 可以利用几何一致性和全局布局；
- 对重复结构、局部歧义更稳；
- 匹配质量通常比最近邻 + ratio test 更高。

对于月球影像，SuperGlue 的潜在优势是：

- 陨石坑、山脊、沟槽存在重复结构；
- 单个局部 patch 可能很像，但整体空间关系不同；
- SuperGlue 可以用点集关系减少误匹配。

但问题是：

- 需要足够好的输入 keypoints；
- 如果 SuperPoint / DISK 提取点本身不稳定，SuperGlue 也救不了；
- 大光照变化下，如果提取到的点集差异很大，匹配仍会失败。

SuperGlue 更适合：

> 有一定数量稳定局部特征，但普通最近邻匹配误匹配较多的场景。

---

### 2.3 LightGlue：现代高效 matcher，工程上很适合做 fallback cascade

LightGlue 可以理解为更轻、更快、更现代的学习式 matcher。它常用于 SuperPoint、DISK、ALIKED、SIFT 等特征的匹配。

优点：

- 比 SuperGlue 通常更快；
- 支持 early stopping；
- 可与多种特征前端组合；
- 工程部署友好；
- 匹配质量通常好于传统最近邻。

对于你的 adaptive routing 场景，LightGlue 很适合做中间层：

- `sift + lightglue`
- `superpoint + lightglue`
- `disk + lightglue`

这样可以把“特征提取”和“匹配器”解耦。

比如：

| 特征前端 | 匹配后端 | 适用场景 |
|---|---|---|
| SIFT | ratio test / LightGlue | 纹理丰富、光照小 |
| SuperPoint | LightGlue | 中等纹理、中等光照变化 |
| DISK | LightGlue | 纹理较弱、需要学习式特征 |
| LoFTR | 内置 detector-free matching | 弱纹理、稀疏特征失败 |

---

### 2.4 LoFTR：提取与匹配是一体的

LoFTR 不太适合简单归类为“特征提取器”或“匹配器”，它是 detector-free matching pipeline。

它的优势来自：

- coarse-to-fine 匹配；
- transformer 全局上下文；
- 不依赖局部关键点检测；
- 能在弱纹理区域建立更多对应。

所以在 fallback cascade 里，LoFTR 很适合作为：

> SIFT / SuperPoint / DISK 失败后的强力回退 matcher。

但它不一定应该总是首选，因为：

- 成本高；
- 速度慢；
- 显存压力大；
- 对极大分辨率 DOM 需要 tile 化；
- 误匹配可能更隐蔽，需要质量门控。

---

## 3. 对月球影像的具体判断

月球影像的困难主要不是“没有纹理”这么简单，而是：

1. **纹理来源复杂**  
   很多可见纹理来自阴影，而阴影不是稳定物体。

2. **太阳高度和方位变化大**  
   同一陨石坑在不同太阳角下，明暗结构可能完全反转。

3. **弱纹理区域多**  
   月海、平坦高地区域可能缺少稳定局部关键点。

4. **重复结构多**  
   大量小坑、碎坑、沟槽形态相似，容易产生错误匹配。

5. **尺度和投影差异可能叠加**  
   DOM、ORI、投影变换、局部地形起伏都会影响匹配。

因此，算法选择可以这样分层：

### 光照差异小 + 纹理丰富

优先：

- SIFT；
- RootSIFT；
- SIFT + LightGlue；
- SIFT + RANSAC。

理由：

- 快；
- 稳；
- 可解释；
- 不受训练域影响。

### 光照中等变化 + 有清晰地形结构

优先：

- SuperPoint + LightGlue；
- DISK + LightGlue；
- SuperPoint + SuperGlue；
- DISK + SuperGlue。

理由：

- 比 SIFT 更能处理局部外观变化；
- matcher 能利用上下文减少误匹配；
- 适合陨石坑、山脊、沟槽等结构。

### 弱纹理 + sparse 特征数量不足

优先：

- LoFTR；
- ASpanFormer；
- DKM；
- RoMa 类 dense matching 方法，如果工程允许。

理由：

- 不依赖显式关键点；
- 利用图像间上下文；
- 能在 SIFT/SuperPoint 点数不足时给出匹配。

### 大光照差异 + 阴影变化明显

不能只靠 matcher，建议：

- 先做 texture / illumination probe；
- 用 shadow mask 或边缘结构抑制阴影伪特征；
- 加 DEM render probe；
- 根据太阳几何路由 matcher；
- 用严格质量门控决定是否 fallback。

这正好对应你计划里的 Phase C / D。

---

## 4. SIFT 与深度学习方法的优点对比

### SIFT 的核心优点

- 不需要训练；
- 泛化强；
- 可解释；
- 对尺度、旋转、普通亮度变化鲁棒；
- 速度和资源消耗低；
- 适合 CPU 批处理；
- 对工程生产非常友好；
- 容易与 RANSAC、bundle adjustment、控制点筛选结合。

### SIFT 的核心短板

- 对弱纹理不友好；
- 对大光照差异和阴影变化不够鲁棒；
- 对重复结构容易误匹配；
- 不利用全局上下文；
- 局部 patch 外观变化大时描述子失效。

---

### 深度学习特征/匹配的核心优点

- 可学习更鲁棒的描述子；
- 能处理更复杂的外观变化；
- matcher 可以利用上下文；
- 对弱纹理、重复纹理可能更稳；
- detector-free 方法能在少关键点区域工作；
- 适合复杂宽基线和非理想光照场景；
- 和置信度输出结合后，适合做质量门控。

### 深度学习方法的核心短板

- 依赖训练域；
- 月球影像可能存在 domain gap；
- 计算成本高；
- 显存压力大；
- tile 化后上下文可能被截断；
- 出错时可解释性较差；
- 高置信错误匹配仍然可能发生；
- 生产环境依赖复杂。

---

## 5. 推荐的 adaptive routing 策略

你现在的方向可以进一步抽象成这样：

```text
pair probe
  ↓
判断纹理强度、光照差异、预估阴影影响
  ↓
选择 initial matcher
  ↓
执行匹配
  ↓
质量门控：inlier count / ratio / coverage / residual
  ↓
如果失败，按 fallback chain 切换 matcher
```

一个合理的 cascade 可以是：

### 场景 A：纹理丰富、光照小

```text
SIFT → SIFT+LightGlue → SuperPoint+LightGlue → LoFTR
```

### 场景 B：纹理中等、光照中等

```text
SuperPoint+LightGlue → DISK+LightGlue → LoFTR → SIFT
```

### 场景 C：弱纹理、SIFT 点数少

```text
LoFTR → DISK+LightGlue → SuperPoint+LightGlue
```

### 场景 D：大光照差异、阴影主导

```text
DISK+LightGlue → LoFTR → SuperPoint+LightGlue
```

但注意：**大光照差异不一定 LoFTR 必然最好**。如果阴影形态完全改变，LoFTR 也可能被误导。这时最好结合：

- 太阳高度角；
- 太阳方位角；
- DEM render probe；
- shadow mask；
- gradient/edge-based similarity；
- residual statistics；
- local coverage check。

---

## 6. 对当前实现计划的建议

结合你这个 `Adaptive Lighting Router Implementation Plan`，我建议把算法层面的逻辑表达成：

1. **SIFT 是低成本 baseline**  
   当 texture probe 显示纹理丰富且 lighting gap 小时，优先用 SIFT。

2. **SuperPoint / DISK 是 learned sparse feature fallback**  
   当纹理中等、SIFT 可能不稳、但仍有足够局部结构时使用。

3. **LoFTR 是 weak-texture / sparse-failure fallback**  
   当关键点数量不足、coverage 不够、inlier count 低时，切到 LoFTR。

4. **光照差异大时不要只靠模型名决策**  
   应该把 lighting constraints、render probe、shadow explainability 放进 route decision。

5. **所有 deep matcher 都必须经过质量门控**  
   特别是月球重复坑纹理，很容易产生“看起来很多但几何错误”的匹配。

---

## 简短总结

你的理解可以这样表述：

> 经典 SIFT 适合纹理丰富、光照差异小、局部梯度结构稳定的月球影像匹配；SuperPoint、DISK 等学习式局部特征在中等纹理和一定光照变化下可能更稳；LoFTR 这类 detector-free 深度匹配方法更适合弱纹理、关键点不足或需要上下文推理的场景。但深度方法对月球影像存在训练域差异，不能盲目认为一定优于 SIFT，必须配合几何验证、残差统计、覆盖率检查和 adaptive fallback cascade。

换句话说：**SIFT 是强 baseline，深度方法是复杂场景下的增强与回退，真正可靠的是“路由 + 质量门控 + 级联回退”。**

User: 大阴影区域，能否使用一些去除阴影技术？

GitHub Copilot: 可以用，但在月球影像匹配里要非常谨慎：**大阴影区域更推荐“阴影识别 + 降权/遮罩 + 光照归一化”，而不是直接做强去阴影、强补纹理**。

核心原因是：月球大阴影里很多地方不是“亮度低一点”，而是**真实信息缺失或信噪比极低**。如果用深度去阴影模型把暗区“补亮”，可能会生成看起来合理但并不存在的纹理，反而给 SIFT / SuperPoint / LoFTR 制造伪特征，控制点会更危险。

## 可以用哪些技术

### 1. 阴影 mask：最稳妥，优先级最高

先检测大阴影区域，然后在特征提取和匹配时：

- 阴影区域不提点；
- 或者降低匹配权重；
- 或者只允许阴影外区域参与几何估计；
- 或者 shadow / non-shadow 分区分别匹配。

简单可用的 shadow mask 方法包括：

- 灰度阈值；
- 局部自适应阈值；
- 低亮度 + 低纹理联合判断；
- 边缘附近保留，纯黑阴影内部剔除；
- 如果有太阳几何和 DEM，可用地形投影阴影预测。

对月球 DOM 匹配来说，这通常比“去阴影”更可靠。

---

### 2. 光照归一化：适合轻中度阴影，不适合纯黑阴影

可以对影像做一些 photometric normalization，让光照差异变小：

- CLAHE：局部直方图均衡；
- gamma correction；
- log transform；
- homomorphic filtering；
- Retinex；
- high-pass / low-pass 分离；
- local contrast normalization；
- Z-score / percentile normalization。

这些方法对 **轻度阴影、整体曝光差、局部对比度差** 有帮助。

但如果阴影区已经接近黑色、细节丢失严重，归一化只是把噪声放大，不会恢复真实地形纹理。

---

### 3. 使用梯度、边缘或结构特征代替灰度特征

对于阴影差异大的区域，可以降低对原始灰度的依赖，改用更结构化的表达：

- gradient magnitude；
- Canny / Sobel edge；
- phase congruency；
- Census transform；
- rank transform；
- local binary pattern；
- normalized gradient correlation。

这些表达对亮度变化更鲁棒。  
对 SIFT 来说，也可以尝试在归一化图、梯度图或边缘增强图上提特征。

但注意：月球阴影边界本身会随太阳角移动，所以**阴影边界不一定是稳定地物边界**。这类边缘要结合几何验证过滤。

---

### 4. DEM + 太阳几何的物理光照校正

如果有 DEM、SPICE、太阳高度角/方位角，这条路线更适合月球影像：

1. 根据 DEM 和太阳方向估计地形阴影；
2. 生成 Lambertian / Hapke / Lommel-Seeliger 光照模型；
3. 对真实影像做地形光照归一化；
4. 或者生成 synthetic render，与真实图做结构 probe；
5. 判断哪些纹理是地形本体，哪些更可能是光照阴影。

这比纯图像去阴影更物理、更可解释。

你当前计划里的 **DEM render probe** 就很适合承担这个角色：不是简单“修图”，而是判断当前 pair 是否被阴影主导，并辅助 matcher 路由。

---

### 5. 深度学习去阴影：可以试，但不建议直接用于控制点生产

自然图像里的 shadow removal 网络可以把阴影区域变亮、补颜色、增强纹理。但用于月球影像有几个风险：

- 训练域通常不是月球影像；
- 可能 hallucinate 纹理；
- 可能改变真实灰度关系；
- 可能让 matcher 产生高置信伪匹配；
- 对控制网、几何测量不够可解释。

如果要用，建议只作为：

- 可视化增强；
- 候选匹配预处理分支；
- 低权重 fallback；
- 或者与原图匹配结果做交叉验证。

不建议把深度去阴影后的纹理直接当作可靠几何证据。

---

## 对不同 matcher 的影响

### SIFT

大阴影会让 SIFT 出现两个问题：

1. 纯暗区提不出稳定点；
2. 阴影边界可能产生大量伪特征。

建议：

- 对纯阴影区 mask；
- 对轻阴影区做 CLAHE / Retinex；
- 用 RootSIFT；
- 匹配后加强 RANSAC 和 coverage 检查。

### SuperPoint / DISK

学习式特征可能比 SIFT 更能处理局部外观变化，但仍会受大阴影影响。

建议：

- 输入前做轻度光照归一化；
- 保留 shadow mask；
- 避免让纯黑阴影区域贡献高置信关键点；
- 用 LightGlue / SuperGlue 的上下文能力筛掉局部伪匹配。

### LoFTR

LoFTR 对弱纹理更友好，但大阴影也可能误导它。尤其是阴影形状在两幅图中变化很大时，LoFTR 可能把阴影轮廓当成匹配结构。

建议：

- 对纯阴影区 mask 或降权；
- 分 tile 判断 shadow ratio；
- shadow ratio 太高的 tile 不进入 LoFTR；
- 或者只在非阴影 overlap 充足时启用 LoFTR；
- 匹配后必须看 inlier ratio、coverage 和 residual。

---

## 推荐工程策略

我建议不要设计成单一的“去阴影开关”，而是做成 adaptive routing 的一个 photometric preprocessing / shadow handling profile：

### Profile 1：`none`

不处理阴影，适合光照接近、纹理清晰的 pair。

### Profile 2：`normalize`

轻量光照归一化：

- percentile clipping；
- CLAHE；
- gamma/log correction；
- local contrast normalization。

适合轻中度阴影。

### Profile 3：`mask`

检测大阴影并遮罩：

- 纯暗区不提点；
- tile shadow ratio 过高则跳过；
- matcher 只使用非阴影区域。

适合大阴影区域。

### Profile 4：`render-aware`

结合 DEM / SPICE：

- 预测阴影；
- 做地形光照解释；
- 判断真实纹理是否被阴影主导；
- 参与 matcher route decision。

适合后续 Phase C / D。

---

## 一个比较稳的匹配流程

可以这样接入：

1. 低分辨率 preview 计算 shadow ratio；
2. 如果 shadow ratio 很低：走普通 SIFT / SuperPoint；
3. 如果 shadow ratio 中等：做光照归一化后匹配；
4. 如果 shadow ratio 高：启用 shadow mask，跳过大阴影 tile；
5. 如果非阴影区域太少：标记 pair 为低可信，进入 fallback 或人工复核；
6. 如果有 DEM / SPICE：用 render probe 判断阴影是否可解释；
7. 所有结果都经过质量门控：
   - inlier count；
   - inlier ratio；
   - spatial coverage；
   - mean residual；
   - p95 residual；
   - shadow/non-shadow 区域分布。

---

## 简短建议

可以使用去阴影技术，但我建议按优先级这样做：

1. **先做 shadow mask**：不要让纯黑阴影区参与特征和控制点生成。  
2. **再做轻量光照归一化**：CLAHE / Retinex / local normalization，处理轻中度阴影。  
3. **不要盲目用深度去阴影补纹理**：容易生成伪结构。  
4. **后续结合 DEM + 太阳几何**：这是月球影像更可靠的“物理去阴影/光照解释”方向。  
5. **把 shadow ratio 写入 adaptive routing metadata**：让 matcher 选择和质量门控有证据可追溯。

一句话：**大阴影区域不是简单“去掉阴影”就能恢复匹配，生产上更稳的是“识别阴影、避开阴影、归一化轻阴影、用物理模型解释阴影”。**

User: 你还有什么思路可以自动分析出月球ＬＲＯ　ＮＡＣ影像是纹理丰富，还是纹理稀少？

GitHub Copilot: 可以，而且我建议不要只判断“图像看起来有没有纹理”，而是判断 **“对匹配有用的稳定纹理是否足够”**。对月球 LRO NAC 来说尤其重要，因为很多强纹理其实是**阴影纹理**，太阳角一变就不稳定；而真正可靠的是撞击坑边缘、岩块、沟槽、坡折、山脊等相对稳定地形结构。

可以从下面几个层次自动分析。

## 核心思路

把一幅 LRO NAC 或一对 NAC/DOM 图像分成 tiles，然后给每个 tile 计算一组指标：

```text
raw image tile
  ↓
亮度/阴影分析
  ↓
梯度/边缘/频谱/熵分析
  ↓
关键点密度分析
  ↓
自匹配或跨图预匹配分析
  ↓
输出 texture richness / matchability score
```

最终不要只输出一个全图分数，而是输出：

- 全图纹理等级：`rich` / `medium` / `weak` / `shadow-dominated`
- tile 级纹理热力图；
- 可用于匹配的 tile mask；
- 推荐 matcher：`sift` / `superpoint` / `disk` / `loftr`；
- 是否需要 shadow mask / photometric normalization。

---

## 1. 梯度能量：最直接的纹理强度指标

纹理丰富区域通常有较多局部灰度变化。可以计算：

- Sobel 梯度幅值均值；
- Sobel 梯度幅值方差；
- Laplacian 方差；
- structure tensor response；
- Harris/Shi-Tomasi corner response。

例如：

```text
gradient_energy = mean(sqrt(dx^2 + dy^2))
laplacian_var = var(Laplacian(image))
corner_density = count(corner_response > threshold) / tile_area
```

一般来说：

| 指标表现 | 解释 |
|---|---|
| 梯度能量高，角点多 | 纹理丰富，SIFT/SuperPoint 可能有效 |
| 梯度能量低，角点少 | 弱纹理，SIFT 可能失败 |
| 梯度能量高但集中在少数边界 | 可能是阴影边界，不一定可靠 |
| Laplacian 方差低 | 模糊或平坦区域，匹配难 |

但梯度指标有一个陷阱：**阴影边界也会产生很强梯度**。所以不能单独使用。

---

## 2. 局部熵：判断灰度信息量

可以计算 tile 的灰度熵：

$$
H = -\sum_i p_i \log(p_i)
$$

纹理丰富区域通常熵更高，平坦区域熵更低。

适合指标：

- global entropy；
- local entropy map；
- entropy mean；
- entropy std；
- percentile entropy。

判断方式：

| 熵表现 | 解释 |
|---|---|
| 熵高且分布均匀 | 真实纹理可能丰富 |
| 熵低 | 平坦、暗区、过曝或低对比 |
| 熵高但 shadow ratio 高 | 可能是阴影造成的伪纹理 |
| 熵高但关键点少 | 可能是噪声或细碎不可匹配纹理 |

对 LRO NAC，熵适合用来快速区分：

- 月海平坦区；
- 高地区破碎地貌；
- 大型阴影区；
- 撞击坑密集区。

---

## 3. 频谱分析：区分平滑区、细纹理和噪声

可以对 tile 做 FFT 或小波分析，看高频能量比例：

```text
high_freq_ratio = high_frequency_energy / total_energy
mid_freq_ratio = mid_frequency_energy / total_energy
```

纹理丰富的地形通常中高频能量较高；平坦区域高频能量低；噪声区域可能高频能量异常高但结构性差。

推荐关注：

- 中频能量：通常比极高频更可靠；
- 高频/中频比；
- 频谱方向性；
- 多尺度小波能量。

判断：

| 频谱特征 | 解释 |
|---|---|
| 中频能量高 | 有稳定地形纹理 |
| 高频极高但中频低 | 可能是噪声、压缩或锐化伪影 |
| 低频占主导 | 大面积平滑、坡面或光照渐变 |
| 单方向高频强 | 可能是条带噪声、扫描方向伪影或强阴影边界 |

对 NAC 影像，频谱分析还能帮助识别：

- CCD/扫描条带；
- 压缩伪影；
- 过锐化边缘；
- 大尺度光照梯度。

---

## 4. 关键点密度：直接估计 SIFT/SuperPoint 能否工作

这一步非常实用：直接在低分辨率 preview 或 tile 上跑一个轻量 keypoint detector，然后统计：

- SIFT keypoint count；
- SIFT keypoint density；
- keypoint response mean；
- keypoint scale distribution；
- keypoint spatial coverage；
- SuperPoint keypoint density，如果环境允许；
- DISK keypoint density，如果环境允许。

关键不是“点多不多”，而是：

> 点是否覆盖足够广，且不是只集中在阴影边界或图像边缘。

可以定义：

```text
keypoint_density = keypoint_count / tile_area
keypoint_coverage = occupied_grid_cells / total_grid_cells
keypoint_response_median = median(response)
```

判断：

| 情况 | 解释 |
|---|---|
| keypoint density 高，coverage 高 | SIFT/SuperPoint 候选好 |
| keypoint density 高，coverage 低 | 点集中，几何约束不稳 |
| keypoint density 低 | 弱纹理，考虑 LoFTR |
| keypoint 多但 shadow ratio 高 | 可能是阴影伪特征 |

我会特别推荐这个指标，因为它和 matcher 成败直接相关。

---

## 5. 可匹配性分析：比单图纹理更重要

如果你有左右影像 pair，最可靠的不是单图 texture richness，而是 **pair matchability**。

可以做一个低成本预匹配 probe：

1. 下采样到 preview；
2. 在 tile 或全图上跑 SIFT；
3. 做 ratio test；
4. 做 RANSAC；
5. 统计 inlier count、inlier ratio、coverage、residual。

输出：

```text
preview_sift_keypoints_left
preview_sift_keypoints_right
preview_raw_matches
preview_inlier_count
preview_inlier_ratio
preview_inlier_coverage
preview_residual_mean
```

这能直接回答：

> 这对影像对 SIFT 是否够用？

如果 SIFT preview 已经稳定成功，就不需要急着上 LoFTR。  
如果单图看着有纹理，但 preview SIFT inlier 很少，说明纹理可能不可重复，例如光照变化大、阴影移动、重复坑太多。

这比单图判断更接近实际生产需求。

---

## 6. 阴影占比与阴影主导度：月球场景必须加

对 LRO NAC，阴影不是一个附加问题，而是主问题之一。建议每个 tile 计算：

- dark pixel ratio；
- very dark pixel ratio；
- local contrast in dark region；
- shadow edge density；
- non-shadow texture density；
- shadow/non-shadow keypoint ratio。

例如：

```text
shadow_ratio = count(pixel < p5_or_adaptive_threshold) / tile_area
shadow_edge_ratio = edge_pixels_near_shadow_boundary / all_edge_pixels
usable_texture_ratio = texture_score_in_non_shadow / total_texture_score
```

这样可以区分：

| 类型 | 说明 |
|---|---|
| 真实纹理丰富 | 非阴影区域也有大量梯度和角点 |
| 阴影主导纹理 | 大部分梯度来自阴影边界 |
| 纯暗弱纹理 | 阴影区内部几乎没有可靠信息 |
| 光照渐变 | 有亮度变化但缺少局部结构 |

非常关键的一点：

> 对匹配有用的是 `non_shadow_texture_score`，不是总的 `texture_score`。

所以我建议定义一个“可用纹理分数”：

```text
usable_texture_score =
    texture_score
    * non_shadow_area_ratio
    * keypoint_coverage
    * shadow_penalty
```

而不是单纯看梯度或熵。

---

## 7. 多尺度纹理分析：避免误判大坑和平坦坡面

LRO NAC 的地貌尺度变化很大。有些区域在小尺度上看平滑，但大尺度上有坑缘、山脊、坡折；有些区域小尺度有噪声，但没有稳定结构。

建议多尺度计算：

- 原始尺度；
- 1/2 下采样；
- 1/4 下采样；
- 1/8 preview。

每个尺度计算：

- gradient energy；
- entropy；
- corner density；
- keypoint density；
- edge density。

然后形成多尺度 profile：

| 多尺度表现 | 判断 |
|---|---|
| 小尺度和中尺度都强 | 纹理丰富 |
| 小尺度弱，中尺度强 | 大型地形结构，适合 LoFTR/区域匹配 |
| 小尺度强，中尺度弱 | 可能是噪声或细碎纹理 |
| 所有尺度都弱 | 真弱纹理 |
| 只有阴影边界尺度强 | 阴影主导 |

这个对月球很有用，因为撞击坑、山脊、沟槽的尺度差异非常大。

---

## 8. 结构一致性：区分地形纹理和噪声纹理

可以分析纹理是否具有稳定结构，而不是随机噪声：

- edge connected components；
- line/arc structure density；
- contour length distribution；
- blob/crater-like response；
- Gabor filter bank response；
- structure tensor coherence。

例如：

```text
coherence = (lambda1 - lambda2) / (lambda1 + lambda2)
```

其中 $\lambda_1, \lambda_2$ 是 structure tensor 的特征值。

判断：

| 结构表现 | 解释 |
|---|---|
| 多方向结构丰富 | 撞击坑/碎石/复杂地貌，适合局部特征 |
| 单方向强结构 | 山脊、沟槽、条带或阴影边界 |
| 随机高频 | 噪声或压缩伪影 |
| 大面积低结构 | 弱纹理 |

---

## 9. 结合 NAC metadata / SPICE 的先验

如果能读 LRO NAC label 或 SPICE 几何，建议把这些也作为纹理判定的辅助信息：

- incidence angle；
- emission angle；
- phase angle；
- solar elevation；
- solar azimuth；
- pixel scale；
- exposure / gain / compression 信息；
- map projection / resolution；
- 是否处于极区低太阳高度场景。

例如：

| 几何条件 | 影响 |
|---|---|
| incidence angle 很大 | 阴影更长，光照伪纹理更多 |
| solar elevation 很低 | 大阴影风险高 |
| phase angle 大 | 明暗变化强，SIFT 稳定性下降 |
| emission angle 大 | 视角变形更大 |
| 分辨率差异大 | 尺度匹配难度上升 |

如果 metadata 显示太阳高度极低，即使图像梯度很强，也应该增加 shadow penalty。

---

## 10. 深度特征自信度：如果有环境，可以作为高级指标

如果 deep-learning 环境可用，可以跑轻量 deep feature probe：

- SuperPoint keypoint density；
- SuperPoint confidence map；
- DISK detection confidence；
- LightGlue match confidence；
- LoFTR coarse confidence；
- LoFTR match density。

但我不建议一开始就依赖它们，因为：

- 成本高；
- 环境依赖重；
- 月球 domain gap 存在；
- 解释性弱。

更合理的是：

```text
classic texture probe first
  ↓
如果不确定，再跑 deep probe
```

比如：

| classic probe 结果 | deep probe 用途 |
|---|---|
| 明显 rich | 不必跑，直接 SIFT |
| 明显 weak | 可以直接 LoFTR 或跳过 |
| ambiguous | 跑 SuperPoint/DISK/LoFTR confidence probe |
| shadow-dominated | 先 shadow mask，再 deep probe |

---

## 推荐的自动评分指标

可以设计一个综合评分：

```text
texture_richness_score =
    0.25 * normalized_gradient_energy
  + 0.20 * normalized_entropy
  + 0.20 * normalized_keypoint_density
  + 0.20 * keypoint_coverage
  + 0.15 * mid_frequency_energy
  - 0.30 * shadow_dominance
  - 0.20 * noise_or_stripe_penalty
```

再单独定义一个更重要的：

```text
matchability_score =
    0.30 * preview_inlier_ratio
  + 0.25 * preview_inlier_count_score
  + 0.20 * preview_spatial_coverage
  + 0.15 * non_shadow_texture_score
  - 0.10 * residual_penalty
```

我建议区分两个概念：

| 分数 | 作用 |
|---|---|
| `texture_richness_score` | 判断单图是否纹理丰富 |
| `matchability_score` | 判断这对图像是否容易匹配 |
| `shadow_dominance_score` | 判断纹理是否主要来自阴影 |
| `sift_viability_score` | 判断 SIFT 是否值得首选 |
| `deep_matcher_need_score` | 判断是否需要 SuperPoint/DISK/LoFTR |

其中最实用的是 `sift_viability_score`：

```text
sift_viability_score =
    keypoint_density
  * keypoint_coverage
  * non_shadow_area_ratio
  * preview_inlier_ratio
```

如果这个分数高，SIFT 优先。  
如果 keypoint density 低但中尺度结构还在，LoFTR 优先。  
如果 keypoint 有一些但传统匹配差，SuperPoint/DISK + LightGlue 优先。

---

## 建议的分类规则

可以先用规则版，不急着训练模型。

### `rich_texture`

满足：

- 梯度能量高；
- entropy 高；
- SIFT/SuperPoint keypoint density 高；
- keypoint coverage 高；
- shadow dominance 低；
- preview SIFT inlier ratio 好。

推荐：

```text
SIFT → SIFT+LightGlue → SuperPoint+LightGlue
```

### `medium_texture`

满足：

- 有一定角点和边缘；
- coverage 尚可；
- SIFT inlier 不稳定；
- 光照差异中等。

推荐：

```text
SuperPoint+LightGlue → DISK+LightGlue → SIFT → LoFTR
```

### `weak_texture`

满足：

- 梯度低；
- entropy 低；
- SIFT keypoint 少；
- coverage 差；
- 但中尺度结构可能还存在。

推荐：

```text
LoFTR → DISK+LightGlue → SuperPoint+LightGlue
```

### `shadow_dominated`

满足：

- shadow ratio 高；
- 梯度集中在阴影边界；
- 非阴影区域 texture score 低；
- preview matches 大多落在 shadow boundary 附近。

推荐：

```text
shadow mask / normalize
  ↓
DISK+LightGlue 或 LoFTR
  ↓
严格质量门控
  ↓
必要时标记人工复核
```

### `unmatchable_or_low_confidence`

满足：

- 非阴影可用区域太少；
- 关键点太少；
- preview inlier 极低；
- residual 高；
- coverage 差。

推荐：

```text
跳过 / 降级 / 人工复核 / 等待 DEM render probe
```

---

## 可以写入 metadata 的字段

为了后续数据驱动调参，建议每次匹配都记录这些字段：

```yaml
texture_probe:
  gradient_energy_mean:
  gradient_energy_p90:
  laplacian_variance:
  entropy_mean:
  entropy_p50:
  mid_frequency_ratio:
  sift_keypoint_count:
  sift_keypoint_density:
  keypoint_coverage:
  shadow_ratio:
  shadow_edge_ratio:
  non_shadow_texture_score:
  texture_richness_score:
  shadow_dominance_score:
  sift_viability_score:
  matchability_score:
  texture_class:
  recommended_initial_matcher:
```

如果是 pair 级 preview probe，再记录：

```yaml
pair_probe:
  preview_sift_matches:
  preview_sift_inliers:
  preview_sift_inlier_ratio:
  preview_sift_coverage:
  preview_sift_mean_residual:
  preview_sift_p95_residual:
```

这些信息后面可以反过来训练一个轻量 router。

---

## 我最推荐的落地版本

第一版不要复杂，建议这样做：

1. 低分辨率 preview 分 tile；
2. 每个 tile 计算：
   - entropy；
   - Sobel gradient energy；
   - Laplacian variance；
   - SIFT keypoint density；
   - keypoint coverage；
   - shadow ratio；
   - non-shadow texture score；
3. 如果有 pair，额外跑 preview SIFT + RANSAC；
4. 根据规则输出：
   - `rich_texture`
   - `medium_texture`
   - `weak_texture`
   - `shadow_dominated`
   - `low_confidence`
5. 把结果传给 adaptive routing；
6. 把所有指标写入 sidecar。

这版成本低、解释性强、适合先接到你现在的 `adaptive_routing.py` 里。

---

## 一个简单的决策例子

```text
if shadow_ratio > 0.45 and non_shadow_texture_score < threshold:
    texture_class = "shadow_dominated"
    matcher = "disk" or "loftr"
    preprocessing = "shadow_mask"

elif sift_keypoint_density high and keypoint_coverage high and preview_inlier_ratio high:
    texture_class = "rich_texture"
    matcher = "sift"

elif keypoint_density medium and preview_sift unstable:
    texture_class = "medium_texture"
    matcher = "superpoint_lightglue" or "disk_lightglue"

elif keypoint_density low and entropy low:
    texture_class = "weak_texture"
    matcher = "loftr"

else:
    texture_class = "low_confidence"
    matcher = "cascade"
```

---

## 和 adaptive routing 的关系

你现在的 adaptive router 可以增加一个更明确的 probe 层：

```text
ImageTextureProbe
  + gradient_energy
  + entropy
  + keypoint_density
  + keypoint_coverage
  + shadow_ratio
  + non_shadow_texture_score
  + texture_class
  + sift_viability_score
```

然后 route decision 可以更清楚：

| texture probe 结果 | route |
|---|---|
| `rich_texture` + low lighting gap | `sift` |
| `medium_texture` | `superpoint` / `disk` |
| `weak_texture` | `loftr` |
| `shadow_dominated` | `shadow-mask + disk/loftr` |
| `low_confidence` | `cascade` or manual review |

这样比单纯“弱纹理走 LoFTR、丰富纹理走 SIFT”更稳，因为它考虑了阴影是否在伪装成纹理。

---

## 结论

我最推荐的自动分析方法是：

> **多尺度 tile 纹理 probe + shadow dominance 分析 + keypoint density/coverage + preview SIFT 可匹配性测试。**

其中最关键的不是判断“纹理多不多”，而是判断：

1. **非阴影区域是否有纹理；**
2. **关键点是否足够多且空间覆盖好；**
3. **这些纹理在左右影像间是否可重复匹配；**
4. **强梯度是否主要来自移动阴影边界；**
5. **SIFT 是否已经足够，还是需要深度 matcher。**

一个实用的首版路线是：

- 单图：`entropy + gradient + keypoint density + shadow ratio`
- pair：`preview SIFT + RANSAC`
- 输出：`texture_class + sift_viability_score + recommended_matcher`

这会比只凭经验选 SIFT / SuperPoint / DISK / LoFTR 稳很多，也非常适合接入你当前的 adaptive lighting router。

- [x] 从单图纹理指标说明自动判断方法  
- [x] 从 pair 级可匹配性说明更可靠的判断方法  
- [x] 单独考虑 LRO NAC 的阴影、太阳角和弱纹理问题  
- [x] 给出可落地的 scoring / metadata / routing 设计  
- [x] 说明如何映射到 SIFT、SuperPoint、DISK、LoFTR 选择策略