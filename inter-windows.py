# 交互窗口成为选项类，脚本代码出现或多或少的错误

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
    "model": "DeepSeek-R1",  # 确认模型名称正确
    "bot_id": "ep-20250306145940-q4mwg",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 2000,
        "temperature": 0.1  # 注意此行结尾需要逗号（如果后续还有参数）
    }  # 正确结束括号
    
    try:
        response = requests.post(
            API_ENDPOINT,
            headers=headers,
            json=payload,
            proxies=PROXIES,
            timeout=15
        )
        response.raise_for_status()
        
        # 调试输出（正确缩进4空格）
        print("火山引擎响应状态:", response.status_code)
        print("原始响应内容:", response.text[:500])  
        
        result = response.json()
        content = result["choices"][0]["message"]["content"]
        
        # 清洗响应内容
        cleaned_content = content.split("```json")[-1].split("```")[0].strip()
        return json.loads(cleaned_content)
        
    except requests.exceptions.RequestException as e:
        print(f"网络请求失败: {str(e)}")
    except (KeyError, json.JSONDecodeError) as e:
        print(f"响应解析错误: {str(e)}")
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
import bpy

# 严格遵守Blender命名规范
class VOLC_PT_EnginePanel(bpy.types.Panel):  # 类名和bl_idname必须包含_PT_
    bl_label = "火山引擎-土木建模"
    bl_idname = "VOLC_PT_MAIN_PANEL"  # 强制包含_PT_标识
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = '智能建造'

    # 正确实现的draw方法（关键修正点）
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        # 专业级参数输入
        col = layout.column(align=True)
        col.prop(scene, "volc_span_length", text="跨径(m)")
        col.prop(scene, "volc_material_type", text="结构材料")
        
        # 动态显示专业参数
        if scene.volc_material_type == 'CONCRETE':
            col.prop(scene, "volc_concrete_grade", text="混凝土强度")
        elif scene.volc_material_type == 'STEEL':
            col.prop(scene, "volc_steel_type", text="钢材型号")
        
        # 添加工程操作按钮
        layout.operator("volc.generate_bridge", 
                       icon='MOD_BUILD',
                       text="生成三维模型")

# 工程属性组（符合土木工程规范）
class VolcProperties(bpy.types.PropertyGroup):
    span_length: bpy.props.FloatProperty(
        name="跨径",
        min=10.0,
        max=200.0,
        default=50.0,
        unit='LENGTH',
        description="桥梁主跨长度"
    )
    
    material_type: bpy.props.EnumProperty(
        name="材料类型",
        items=[
            ('CONCRETE', '混凝土', '普通/预应力混凝土'),
            ('STEEL', '钢结构', '钢箱梁/桁架结构'),
        ],
        default='CONCRETE'
    )

# 工程操作器（含专业验证）
class VOLC_OT_GenerateBridge(bpy.types.Operator):
    bl_label = "生成桥梁结构"
    bl_idname = "volc.generate_bridge"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def execute(self, context):
        # 添加专业级参数验证
        if context.scene.volc_span_length < 20.0:
            self.report({'WARNING'}, "跨径不足20米，建议采用简支梁方案")
        else:
            self.report({'INFO'}, "生成连续梁方案")
            
        return {'FINISHED'}

# 统一注册管理
classes = (
    VOLC_PT_EnginePanel,
    VolcProperties,
    VOLC_OT_GenerateBridge
)

def register():
    # 安全注销旧版本
    for cls in classes:
        if hasattr(bpy.types, cls.__name__):
            bpy.utils.unregister_class(cls)
    
    # 正式注册
    for cls in classes:
        bpy.utils.register_class(cls)
    
    # 注册场景属性
    bpy.types.Scene.volc_span_length = bpy.props.FloatProperty(
        name="跨径",
        default=50.0,
        min=10.0,
        max=500.0
    )
    bpy.types.Scene.volc_material_type = bpy.props.EnumProperty(
        items=[
            ('CONCRETE', '混凝土', ''),
            ('STEEL', '钢材', '')
        ],
        default='CONCRETE'
    )

def unregister():
    # 逆序注销
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    
    # 清理场景属性
    del bpy.types.Scene.volc_span_length
    del bpy.types.Scene.volc_material_type

if __name__ == "__main__":
    register()
