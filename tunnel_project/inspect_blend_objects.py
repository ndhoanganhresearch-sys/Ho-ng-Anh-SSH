import bpy, json
print('OBJECT_COUNT', len(bpy.data.objects))
for obj in bpy.data.objects:
    if any(k in obj.name.lower() for k in ['target','scanner','station','lining','rail','walkway','light','cable']):
        print('OBJ', obj.name, obj.type, tuple(round(v,3) for v in obj.location), tuple(round(v,3) for v in obj.dimensions))
