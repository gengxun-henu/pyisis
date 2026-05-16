import cv2
import torch
import numpy as np
from superpoint import SuperPoint # 确保已安装 superpoint 库

class SuperPointMatcher:
    def __init__(self, device='cuda'):
        self.device = torch.device(device if torch.cuda.is_available() else 'cpu')
        
        # 1. 初始化 SuperPoint 模型
        # nms_radius: 非极大值抑制半径，控制点的密度 (默认4)
        # keypoint_threshold: 置信度阈值，越高点越少但越可靠 (默认0.015)
        config = {
            'nms_radius': 4,
            'keypoint_threshold': 0.015,
            'max_keypoints': -1 # -1 表示不限制数量
        }
        self.model = SuperPoint(config).to(self.device)
        self.model.eval()

    def preprocess(self, img):
        # SuperPoint 输入需要是 Tensor，且归一化到 [0, 1]
        # 增加 batch 维度 (1, 1, H, W)
        img_tensor = torch.from_numpy(img)[None, None].float() / 255.0
        return img_tensor.to(self.device)

    def extract(self, img):
        img_tensor = self.preprocess(img)
        with torch.no_grad():
            # 2. 前向传播
            pred = self.model({'image': img_tensor})
        
        # 3. 提取结果
        # keypoints: [N, 2] (x, y 坐标)
        # descriptors: [N, 256] (描述子向量)
        keypoints = pred['keypoints'][0].cpu().numpy()
        descriptors = pred['descriptors'][0].cpu().numpy()
        
        # OpenCV 的 BFMatcher 需要 float32 类型
        return keypoints, descriptors.T.astype(np.float32)

    def match(self, img1_path, img2_path):
        # 读取图片 (灰度图)
        img1 = cv2.imread(img1_path, cv2.IMREAD_GRAYSCALE)
        img2 = cv2.imread(img2_path, cv2.IMREAD_GRAYSCALE)
        
        if img1 is None or img2 is None:
            raise ValueError("图片读取失败，请检查路径")

        # 提取特征
        kpts1, desc1 = self.extract(img1)
        kpts2, desc2 = self.extract(img2)

        # 4. 特征匹配 (使用 L2 距离，因为 SuperPoint 描述子是浮点型的)
        # SuperPoint 描述子通常已经归一化，所以 L2 距离等价于余弦相似度
        matcher = cv2.BFMatcher(cv2.NORM_L2, crossCheck=False)
        
        # knnMatch 获取每个点的最近邻和次近邻 (用于 Ratio Test)
        matches = matcher.knnMatch(desc1, desc2, k=2)

        # 5. Lowe's Ratio Test (过滤误匹配)
        # 如果最近邻距离 < 0.7 * 次近邻距离，则认为是好匹配
        good_matches = []
        for m, n in matches:
            if m.distance < 0.7 * n.distance:
                good_matches.append(m)

        return kpts1, kpts2, good_matches, img1, img2

    def draw(self, img1, img2, kpts1, kpts2, matches, out_path='superpoint_result.jpg'):
        # OpenCV 的 drawMatches 需要关键点对象，这里简单转换一下
        # 将 numpy 数组转换为 cv2.KeyPoint 对象
        cv_kpts1 = [cv2.KeyPoint(p[0], p[1], 1) for p in kpts1]
        cv_kpts2 = [cv2.KeyPoint(p[0], p[1], 1) for p in kpts2]

        res = cv2.drawMatches(img1, cv_kpts1, img2, cv_kpts2, matches, None, flags=2)
        cv2.imwrite(out_path, res)
        print(f"匹配结果已保存至 {out_path}")

# --- 使用示例 ---
if __name__ == "__main__":
    # 初始化
    sp_matcher = SuperPointMatcher(device='cpu') # 如果没有GPU，改为 'cpu'
    
    # 替换为你的图片路径
    IMG1 = "assets/icl_snippet/250.png" 
    IMG2 = "assets/icl_snippet/251.png"
    
    try:
        kpts1, kpts2, matches, img1, img2 = sp_matcher.match(IMG1, IMG2)
        sp_matcher.draw(img1, img2, kpts1, kpts2, matches)
    except Exception as e:
        print(f"发生错误: {e}")