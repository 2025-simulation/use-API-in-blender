# 可以进行自然语言输入，API 调用失败脚本

import bpy
import requests
import json
from typing import Dict, Optional

# 火山引擎配置（根据控制台信息更新）
VOLC_API_KEY = "9f918ea4-6d6f-491d-8c7d-df5dfdc8c87b"
API_ENDPOINT = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
BOT_ID = "ep-20250306145940-q4mwg"
MODEL_NAME = "DeepSeek-R1"

# 代理配置（根据实际网络情况调整）
PROXIES = {
    "http": "http://127.0.0.1:7890",
    "https": "http://127.0.0.1:7890"
}

def call_volcengine(prompt: str) -> Optional[Dict]:
    """调用火山引擎API服务"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {VOLC_API_KEY}"
    }
    
    # 强化工程专业Prompt设计
    system_prompt = """作为土木工程AI助手，请严格按以下JSON格式响应：
    {
        "structure_type": "结构类型",
        "parameters": {
            "length": 数值（米）,
            "width": 数值（米）,
            "height": 数值（米，可选，默认5）,
            "material": "混凝土/钢材/预应力混凝土",
            "sections": [{
                "shape": "矩形/圆形",
                "尺寸": [长, 宽] 或 [直径],
                "位置": 高程（米）
            }]
        },
        "blender_script": "符合bpy规范的代码"
    }
    规范要求：
    1. 材料强度需满足GB 50010-2010
    2. 截面尺寸需符合JTG D60-2015
    3. 所有数值为整数"""
    
    payload = {
        "model": "DeepSeek-R1",
        "bot_id":  "ep-20250306145940-q4mwg",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 2000,
        "temperature": 0.1
    }
    
    try:
        response = requests.post(
            API_ENDPOINT,
            headers=headers,
            json=payload,
            proxies=PROXIES,
            timeout=15
        )
        response.raise_for_status()
        
        # 调试输出
        print("火山引擎响应状态:", response.status_code)
        print("原始响应内容:", response.text[:500])  # 截取部分内容避免日志过大
        
        result = response.json()
        content = result["choices"][0]["message"]["content"]
        
        # 清洗可能存在的代码注释
        cleaned_content = content.split("```json")[-1].split("```")[0].strip()
        return json.loads(cleaned_content)
        
    except requests.exceptions.RequestException as e:
        print(f"网络请求失败: {str(e)}")
    except (KeyError, json.JSONDecodeError) as e:
        print(f"响应解析错误: {str(e)}")
        print("错误响应内容:", getattr(response, 'text', '无响应'))
    return None

def enhanced_generate_script(params: Dict) -> str:
    """增强版脚本生成，包含工程校验"""
    # 参数校验
    required_fields = ["structure_type", "parameters"]
    if not all(field in params for field in required_fields):
        raise ValueError("缺少必要参数")
    
    # 设置默认高度
    params["parameters"].setdefault("height", 5)
    
    # 生成材质节点
    material_code = f'''
mat = bpy.data.materials.new(name="{params["parameters"]["material"]}")
mat.use_nodes = True
nodes = mat.node_tree.nodes
nodes.clear()
    
# 创建PBR材质节点
bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
bsdf.inputs["Roughness"].default_value = 0.4
    '''
    
    # 生成结构代码
    script = f"""
import bpy
from mathutils import Vector

# 清理场景
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# 创建主结构
bpy.ops.mesh.primitive_cube_add(size=1)
main_obj = bpy.context.object
main_obj.name = '{params["structure_type"]}'

# 设置工程尺寸（单位：米）
main_obj.dimensions = (
    {params["parameters"]["length"]}, 
    {params["parameters"]["width"]}, 
    {params["parameters"]["height"]}
)

# 创建工程材质
{material_code}
main_obj.data.materials.append(mat)

# 生成结构截面
for idx, section in enumerate({params["parameters"]["sections"]}):
    if section["shape"] == "矩形":
        bpy.ops.mesh.primitive_plane_add(
            size=section["尺寸"][0], 
            location=(0, 0, section["位置"])
        )
    elif section["shape"] == "圆形":
        bpy.ops.mesh.primitive_circle_add(
            radius=section["尺寸"][0]/2,
            location=(0, 0, section["位置"])
        )
    section_obj = bpy.context.object
    section_obj.name = f"Section_{{idx+1}}"
    
# 应用变换
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    """
    return script

class VolcEnginePanel(bpy.types.Panel):
    bl_label = "火山引擎-土木建模"
    bl_idname = "PT_VOLC_ENGINE_PANEL"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = '智能建造'

    def draw(self, context):
        layout = self.layout
        layout.prop(context.scene, "eng_input", text="工程指令")
        layout.operator("volc.generate_model")

class VolcEngineOperator(bpy.types.Operator):
    bl_idname = "volc.generate_model"
    bl_label = "生成结构模型"
    
    def execute(self, context):
        user_input = context.scene.eng_input
        response = call_volcengine(user_input)
        
        if not response:
            self.report({'ERROR'}, "API调用失败")
            return {'CANCELLED'}
            
        try:
            if "blender_script" in response:
                # 直接执行API返回的脚本
                exec(response["blender_script"], {"__name__": "__main__"})
            else:
                # 动态生成脚本
                script = enhanced_generate_script(response)
                exec(script, {"__name__": "__main__"})
                
            # 自动调整视图
            bpy.ops.view3d.view_all(use_all_regions=True)
            
        except Exception as e:
            self.report({'ERROR'}, f"脚本错误: {str(e)}")
            return {'CANCELLED'}
            
        return {'FINISHED'}

def register():
    bpy.types.Scene.eng_input = bpy.props.StringProperty(
        name="工程指令",
        default="设计一座跨径50米的预应力混凝土连续梁桥，桥宽12米，梁高2.5米"
    )
    bpy.utils.register_class(VolcEnginePanel)
    bpy.utils.register_class(VolcEngineOperator)

def unregister():
    del bpy.types.Scene.eng_input
    bpy.utils.unregister_class(VolcEnginePanel)
    bpy.utils.unregister_class(VolcEngineOperator)

if __name__ == "__main__":
    register()
