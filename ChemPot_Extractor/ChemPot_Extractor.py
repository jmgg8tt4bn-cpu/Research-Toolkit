import os
import re
import pandas as pd

def extract_vasp_data_advanced():
    # ================= 配置区域 =================
    
    # 1. 设置路径 (根据你的实际情况修改)
    # 建议使用绝对路径，或者确保脚本在 chem_pot 的上一级目录或同级目录
    base_path = r"C:\Users\123\Desktop\Project\My\Workspace\Gua\Gua_dfe\chem_pot"
    
    # 2. 定义文件夹名称列表
    folder_list = [
        "C", "H2", "H3C3N5", "H3N", "H4C", "H4I3N", "H4IN", 
        "H7IN2", "H9C6N11", "HC2N3", "HI3", "I", "IN4", 
        "N2", "Pb", "PbCN2", "PbI2"
    ]

    # 3. 定义你需要提取的元素种类 (这将决定 Excel 的列和不等式的变量)
    target_elements = ["C", "H", "N", "Pb", "I"]

    # 输出文件名
    excel_filename = "chem_pot_data.xlsx"
    txt_filename = "inequalities.txt"

    # ===========================================

    data_list = []
    inequalities = []

    print(f"{'Folder':<15} {'Status':<15} {'Energy':<15} {'Equation'}")
    print("-" * 80)

    for folder in folder_list:
        # 路径拼接: chem_pot/C/scf/POSCAR
        poscar_path = os.path.join(base_path, folder, "scf", "POSCAR")
        outcar_path = os.path.join(base_path, folder, "scf", "OUTCAR")
        
        # 默认数据结构
        entry_data = {
            "Folder": folder,
            "Energy": None,
            "POSCAR_Title": "",
            "Equation": ""
        }
        # 初始化所有目标元素的计数为 0
        for el in target_elements:
            entry_data[el] = 0

        # --- 1. 提取原子数量 (POSCAR 第一行) ---
        if os.path.exists(poscar_path):
            try:
                with open(poscar_path, 'r', encoding='utf-8', errors='ignore') as f:
                    first_line = f.readline().strip()
                    entry_data["POSCAR_Title"] = first_line
                    
                    # 使用正则解析: 匹配 "元素+数字"，例如 H12, C24
                    # 正则解释: ([A-Za-z]+) 匹配字母, \s* 匹配可能的空格, (\d+) 匹配数字
                    matches = re.findall(r"([A-Za-z]+)\s*(\d+)", first_line)
                    
                    # 将提取到的原子数填入字典
                    for el_name, count in matches:
                        if el_name in target_elements:
                            entry_data[el_name] = int(count)
            except Exception:
                entry_data["POSCAR_Title"] = "Read Error"
        
        # --- 2. 提取能量 (OUTCAR) ---
        if os.path.exists(outcar_path):
            try:
                with open(outcar_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    found_energy = False
                    for line in reversed(lines):
                        if "energy  without entropy=" in line:
                            match = re.search(r"energy\s+without\s+entropy=\s*([-.\d]+)", line)
                            if match:
                                entry_data["Energy"] = float(match.group(1))
                                found_energy = True
                                break
            except Exception:
                pass # 保持 Energy 为 None

        # --- 3. 生成不等式字符串 ---
        # 只有当能量存在时才生成不等式
        if entry_data["Energy"] is not None:
            # 构建左边: 54*x_H + 36*x_C ...
            lhs_parts = []
            for el in target_elements:
                count = entry_data[el]
                # 只有原子数大于0才写入不等式
                if count > 0:
                    lhs_parts.append(f"{count}*x_{el}")
            
            if lhs_parts:
                lhs_str = " + ".join(lhs_parts)
                equation_str = f"{lhs_str} <= {entry_data['Energy']:.8f}"
                entry_data["Equation"] = equation_str
                inequalities.append(equation_str)
            else:
                entry_data["Equation"] = "No Atoms Found"
        else:
            entry_data["Equation"] = "No Energy Found"

        # 添加到总列表
        data_list.append(entry_data)
        
        # 打印简报
        status = "OK" if entry_data["Energy"] is not None else "Missing"
        print(f"{folder:<15} {status:<15} {str(entry_data['Energy']):<15} {entry_data['Equation']}")

    # ================= 输出文件 =================

    # 1. 导出 Excel
    df = pd.DataFrame(data_list)
    # 调整列顺序: Folder -> Elements -> Energy -> Equation -> Title
    cols = ["Folder"] + target_elements + ["Energy", "Equation", "POSCAR_Title"]
    df = df[cols]
    
    df.to_excel(excel_filename, index=False)
    print(f"\n[Excel] 表格已生成: {os.path.abspath(excel_filename)}")

    # 2. 导出 Txt (不等式)
    with open(txt_filename, "w") as f_txt:
        for eq in inequalities:
            f_txt.write(eq + "\n")
    print(f"[Txt]   不等式已生成: {os.path.abspath(txt_filename)}")

if __name__ == "__main__":
    extract_vasp_data_advanced()