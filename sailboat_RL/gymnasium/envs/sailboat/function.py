import numpy as np

def calculate_angle_difference(heading_angle, wind_angle):
    """
    计算艏向和绝对风向之间的夹角大小。
    
    参数:
    - heading_angle: 艏向角度（-180°到180°，单位：度）
    - wind_angle: 绝对风向角度（-180°到180°，单位：度）
    
    返回:
    - 两者夹角的大小（单位：度）
    """
    # 将角度从度转换为弧度
    heading_angle_rad = np.radians(heading_angle)
    wind_angle_rad = np.radians(wind_angle)
    
    # 计算角度差，并归一化到 [-π, π]
    angle_diff_rad = (wind_angle_rad - heading_angle_rad + np.pi) % (2 * np.pi) - np.pi
    
    # 取绝对值，得到夹角大小
    angle_diff_deg = np.degrees(abs(angle_diff_rad))
    
    return angle_diff_deg

# 示例
heading_angle = 45  # 艏向角度
wind_angle = -180     # 绝对风向角度
angle_difference = calculate_angle_difference(heading_angle, wind_angle)
print(f"艏向和绝对风向之间的夹角大小为: {angle_difference:.2f}°")