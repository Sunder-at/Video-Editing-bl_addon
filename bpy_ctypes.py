#!/usr/bin/env python3

import bpy
from ctypes import *
from .utility import printc
import math
# Handler type enum. Operator is 3
WM_HANDLER_TYPE_GIZMO = 1
WM_HANDLER_TYPE_UI = 2
WM_HANDLER_TYPE_OP = 3
WM_HANDLER_TYPE_DROPBOX = 4
WM_HANDLER_TYPE_KEYMAP = 5

RNA_MAX_ARRAY_DIMENSION = 3

version = bpy.app.version
functype = type(lambda: None)
as_ptr = bpy.types.bpy_struct.as_pointer


class ListBase(Structure):
    _cache = {}
    _fields_ = (("first", c_void_p), ("last",  c_void_p))
    def __new__(cls, c_type=None):
        if c_type in cls._cache: return cls._cache[c_type]
        elif c_type is None: ListBase_ = cls
        else:
            class ListBase_(Structure):
                __name__ = __qualname__ = f"ListBase{cls.__qualname__}"
                _fields_ = (("first", POINTER(c_type)),
                            ("last",  POINTER(c_type)))
                __iter__ = cls.__iter__
                __bool__ = cls.__bool__
        return cls._cache.setdefault(c_type, ListBase_)

    def __iter__(self):
        links_p = []
        elem_n = self.first or self.last
        elem_p = elem_n and elem_n.contents.prev
        if elem_p:
            while elem_p:
                links_p.append(elem_p.contents)
                elem_p = elem_p.contents.prev
            yield from reversed(links_p)
        while elem_n:
            yield elem_n.contents
            elem_n = elem_n.contents.next

    def __bool__(self):
        return bool(self.first or self.last)


class StructBase(Structure):
    _structs = []
    __annotations__ = {}

    def __init_subclass__(cls):
        cls._structs.append(cls)

    def __new__(cls, srna=None):
        if srna is None:
            return super().__new__(cls)
        if isinstance( srna,  int):
            return cls.from_address(srna)

        try:
            return cls.from_address(as_ptr(srna))
        except AttributeError:
            raise Exception("Not a StructRNA instance")

    # Required
    def __init__(self, *_):
        pass


# blender/source/blender/makesrna/RNA_types.hh
#enum PropertyType
PROP_BOOLEAN = 0,
PROP_INT = 1,
PROP_FLOAT = 2,
PROP_STRING = 3,
PROP_ENUM = 4,
PROP_POINTER = 5,
PROP_COLLECTION = 6,

# source/blender/makesrna/intern/rna_internal_types.hh
class ContainerRNA(StructBase):
    next: c_void_p 
    prev: c_void_p
    prophash: c_void_p # struct GHash
    properties: ListBase

class StructRNA(StructBase):
    cont: ContainerRNA
    identifier: c_char_p
    py_type: c_void_p
    blender_type: c_void_p
    flag: c_int
    prop_tag_defines: c_void_p # const EnumPropertyItem *
    name: c_char_p
    description: c_char_p
    translation_context: c_char_p
    icon: c_int
    nameproperty: lambda: POINTER(PropertyRNA)
    iteratorproperty: lambda: POINTER(PropertyRNA)
    base: lambda: POINTER(StructRNA)
    nested: lambda: POINTER(StructRNA)
    refine: c_void_p # StructRefineFunc 
    path: c_void_p # StructPathFunc 
    reg: c_void_p # StructRegisterFunc 
    unreg: c_void_p # StructUnregisterFunc 
    instance: c_void_p # StructInstanceFunc 
    idproperties: c_void_p # IDPropertiesFunc = IDProperty **(*)(PointerRNA *ptr);
    functions: ListBase

# source/blender/makesrna/intern/rna_internal_types.hh
class PropertyRNA(StructBase):
    next: lambda: POINTER(PropertyRNA)
    prev: lambda: POINTER(PropertyRNA)
    magic: c_int
    identifier: c_char_p
    flag: c_int
    flag_override: c_int
    flag_parameter: c_short
    flag_internal: c_short
    tags: c_short
    name: c_char_p
    description: c_char_p
    icon: c_int
    translation_context: c_char_p
    type: c_int # PropertyType 
    subtype: c_int # PropertySubType 
    getlength: c_void_p # PropArrayLengthGetFunc = int (*)(const PointerRNA *ptr, int length[RNA_MAX_ARRAY_DIMENSION]);
    arraydimension: c_uint
    arraylength: c_uint * RNA_MAX_ARRAY_DIMENSION
    totarraylength: c_uint
    update: c_void_p # UpdateFunc = void (*)(Main *bmain, Scene *active_scene, PointerRNA *ptr);
    noteflag: c_int
    editable: c_void_p # EditableFunc = int (*)(const PointerRNA *ptr, const char **r_info);
    itemeditable: c_void_p # ItemEditableFunc = int (*)(const PointerRNA *ptr, int index);
    override_diff: c_void_p # RNAPropOverrideDiff 
    override_store: c_void_p # RNAPropOverrideStore
    override_apply: c_void_p # RNAPropOverrideApply bool (*)(Main *bmain, RNAPropertyOverrideApplyContext &rnaapply_ctx);
    rawoffset: c_int
    rawtype: c_int # RawPropertyType 
    srna: lambda: POINTER(StructRNA)
    py_data: c_void_p
    # py_data: lambda: POINTER(BPyPropStore)



#  source/blender/makesdna/DNA_ID.h

class ID_Runtime_Remap(StructBase):
    status: c_int
    skipped_refcounted: c_int
    skipped_direct: c_int
    skipped_indirect: c_int

class ID_Runtime(StructBase):
    remap: ID_Runtime_Remap

#  source/blender/makesdna/DNA_ID.h
class ID(StructBase):
    next: c_void_p
    prev: c_void_p
    newid: lambda: POINTER(ID)
    lib: c_void_p # Library
    asset_data: c_void_p # AssetMetaData
    name: c_char * 66
    flag: c_short
    tag: c_int
    us: c_int
    icon_id: c_int
    recalc: c_uint
    recalc_up_to_undo_push: c_uint
    recalc_after_undo_push: c_uint
    session_uid: c_uint
    properties: lambda: POINTER(IDProperty)
    override_library: c_void_p # IDOverrideLibrary
    orig_id: lambda: POINTER(ID)
    py_instance: c_void_p
    library_weak_reference: c_void_p #LibraryWeakReference
    runtime: ID_Runtime


# source/blender/makesdna/DNA_ID.h

class IDPropertyUIData(StructBase):
    description: c_char_p
    rna_subtype: c_int
    _pad: c_char * 4

class IDPropertyData(StructBase):
    pointer: c_void_p
    group: ListBase
    val: c_int
    val2: c_int


class IDProperty(StructBase):
    next: lambda: POINTER(IDProperty)
    prev: lambda: POINTER(IDProperty)
    type: c_char
    subtype: c_char
    flag: c_short
    name: c_char * 64
    _pad0: c_char * 4
    data: IDPropertyData
    len: c_int
    totallen: c_int
    ui_data: lambda: POINTER(IDPropertyUIData)

# source/blender/makesrna/RNA_types.hh
class PointerRNA(StructBase):
    owner_id: lambda: POINTER(ID)
    type: lambda: POINTER(StructRNA)
    data: c_void_p

# source/blender/makesrna/RNA_types.hh
class ExtensionRNA(StructBase):
    data: c_void_p
    srna: lambda: POINTER(StructRNA)
    call: c_void_p # StructCallbackFunc 
    free: c_void_p # StructFreeFunc 

class wmOperatorTypeMacro(StructBase):
    next: lambda: POINTER(wmOperatorTypeMacro)
    prev: lambda: POINTER(wmOperatorTypeMacro)
    idname: c_char * 64 # /* OP_MAX_TYPENAME */
    properties: lambda: POINTER(IDProperty)
    ptr: lambda: POINTER(PointerRNA)

# source/blender/makesdna/DNA_windowmanager_types.h

class wmKeyMap(StructBase):
    next: lambda: POINTER(wmKeyMap)
    prev: lambda: POINTER(wmKeyMap)
    items: ListBase
    diff_items: ListBase
    idname: c_char * 64
    spaceid: c_short
    regionid: c_short
    owner_id: c_char * 64
    flag: c_short
    kmi_id: c_short
    poll: c_void_p #bool (*poll)(struct bContext *);
    poll_modal_item: c_void_p #bool (*poll_modal_item)(const struct wmOperator *op, int value);
    modal_items: c_void_p
  
# source/blender/windowmanager/WM_types.h

class wmOperatorType(StructBase):
    name: c_char_p
    idname: c_char_p
    translation_context: c_char_p
    description: c_char_p
    undo_group: c_char_p
    exec: c_void_p #   int (*exec)(struct bContext *, struct wmOperator *) ATTR_WARN_UNUSED_RESULT;
    check: c_void_p #   bool (*check)(struct bContext *, struct wmOperator *);
    invoke: c_void_p
    #   int (*invoke)(struct bContext *,
                # struct wmOperator *,
                # const struct wmEvent *) ATTR_WARN_UNUSED_RESULT;
    cancel: c_void_p #   void (*cancel)(struct bContext *, struct wmOperator *);
    modal: c_void_p
    #   int (*modal)(struct bContext *,
            #    struct wmOperator *,
            #    const struct wmEvent *) ATTR_WARN_UNUSED_RESULT;
    poll: c_void_p #   bool (*poll)(struct bContext *) ATTR_WARN_UNUSED_RESULT;
    poll_property: c_void_p
    #   bool (*poll_property)(const struct bContext *C,
                        # struct wmOperator *op,
                        # const PropertyRNA *prop) ATTR_WARN_UNUSED_RESULT;
    ui: c_void_p #   void (*ui)(struct bContext *, struct wmOperator *);
    get_name: c_void_p #   const char *(*get_name)(struct wmOperatorType *, struct PointerRNA *);
    get_description: c_void_p #   char *(*get_description)(struct bContext *C, struct wmOperatorType *, struct PointerRNA *);
    srna: lambda: POINTER(StructRNA)
    last_properties: lambda: POINTER(IDProperty)
    prop: lambda: POINTER(PropertyRNA)
    macro: ListBase(wmOperatorTypeMacro)
    modalkeymap: lambda: POINTER(wmKeyMap) #   bool (*pyop_poll)(struct bContext *, struct wmOperatorType *ot) ATTR_WARN_UNUSED_RESULT;
    pyop_poll: c_void_p
    rna_ext: ExtensionRNA
    cursor_pending: c_int
    flag: c_short

# source\blender\windowmanager\wm_event_system.h
class wmEventHandler(StructBase):
    next:   lambda: POINTER(wmEventHandler)
    prev:   lambda: POINTER(wmEventHandler)
    type:   c_int
    flag:   c_char
    poll:   c_void_p

# source\blender\makesdna\DNA_windowmanager_types.h
class wmWindow(StructBase):
    next:                   lambda: POINTER(wmWindow)
    prev:                   lambda: POINTER(wmWindow)

    ghostwin:               c_void_p
    gpuctx:                 c_void_p

    parent:                 lambda: POINTER(wmWindow)

    scene:                  c_void_p
    new_scene:              c_void_p
    view_layer_name:        c_char * 64

    if version >= (3, 3):
        unpinned_scene:     c_void_p  # Scene

    workspace_hook:         c_void_p
    global_areas:           ListBase * 3  # ScrAreaMap

    screen:                 c_void_p  # bScreen  # (deprecated)

    if version > (2, 92):
        winid:              c_int

    pos:                    c_short * 2
    size:                   c_short * 2
    windowstate:            c_char
    active:                 c_char

    if version < (3, 0):
        _pad0:              c_char * 4

    cursor:                 c_short
    lastcursor:             c_short
    modalcursor:            c_short
    grabcursor:             c_short

    if version >= (3, 5, 0):
        pie_event_type_lock: c_short
        pie_event_type_last: c_short

    addmousemove:           c_char
    tag_cursor_refresh:     c_char

    if version <= (2, 93):
        winid:                          c_int

    if version > (2, 93):
        event_queue_check_click:        c_char
        event_queue_check_drag:         c_char
        event_queue_check_drag_handled: c_char

    if version < (3, 5, 0):
        _pad0:                                  c_char * 1
    else:
        event_queue_consecutive_gesture_type:   c_char
        event_queue_consecutive_gesture_xy:     c_int * 2
        event_queue_consecutive_gesture_data:   c_void_p  # wmEvent_ConsecutiveData

    if version < (3, 5, 0):
        pie_event_type_lock:    c_short
        pie_event_type_last:    c_short

    eventstate:             c_void_p
    
    if version > (3, 1):
        event_last_handled: c_void_p

    else:
        tweak:                  c_void_p

    ime_data:               c_void_p  # wmIMEData
    event_queue:            ListBase
    handlers:               ListBase(wmEventHandler)
    modalhandlers:          ListBase(wmEventHandler)
    gesture:                ListBase
    stereo3d_format:        c_void_p
    drawcalls:              ListBase
    cursor_keymap_status:   c_void_p

NUM_STR_REP_LEN = 64
NUM_MAX_ELEMENTS = 3

class wmOperator(StructBase):
    next: lambda: POINTER(wmOperator)
    prev: lambda: POINTER(wmOperator)
    idname : c_char * 64
    properties: lambda: POINTER(IDProperty)
    type: lambda: POINTER(wmOperatorType)
    customdata: c_void_p
    py_instance: c_void_p
    ptr: lambda: POINTER(PointerRNA)
    reports: c_void_p       #ReportList
    macro: ListBase(wmKeyMap)
    opm: lambda: POINTER(wmOperator)
    layout: c_void_p        #uiLayout
    flag: c_short
    _pad: c_char * 6

# source/blender/windowmanager/wm_event_system.hh

class wmEventHandler_Op(StructBase):

    class context(StructBase):  # Anonymous
        win:            lambda: POINTER(wmWindow)
        area:           c_void_p        # ScrArea ptr
        region:         c_void_p        # ARegion ptr
        region_type:    c_short

    head:               wmEventHandler
    op:                 lambda: POINTER(wmOperator)
    is_file_select:     c_bool
    context:            context

    del context


def init_structs():
    for struct in StructBase._structs:
        fields = []
        anons = []
        for key, value in struct.__annotations__.items():
            if isinstance(value, functype):
                value = value()
            elif isinstance(value, Union):
                anons.append(key)
            fields.append((key, value))

        if anons:
            struct._anonynous_ = anons

        # Base classes might not have _fields_. Don't set anything.
        if fields:
            struct._fields_ = fields
        struct.__annotations__.clear()

    StructBase._structs.clear()
    ListBase._cache.clear()

def get_running_op(window) -> str | None: pass


def get_running_op_3_x_x(window) -> str | None:
    win = wmWindow(window)
    for handle in win.modalhandlers:
        if handle.type == WM_HANDLER_TYPE_OP:
            handlec = wmEventHandler_Op(addressof(handle))
            return bytes.decode(handlec.op.contents.type.contents.idname)
    return None

def get_running_op_4_x_x(window) -> str | None:
    for mop in window.modal_operators:
        if mop.bl_idname.__len__() > 0:
            return mop.bl_idname
    return None
            

if bpy.app.version < (4, 0, 0):
    get_running_op = get_running_op_3_x_x
else:
    get_running_op = get_running_op_4_x_x

def calc_bezier(v1, v2, v3, v4, point) -> float:
    def sqrt3d(dd: float) -> float:
        if dd == 0.0: return 0.0
        return math.copysign(1.0 ,dd) * math.exp(math.log(abs(dd)) / 3.0)

    def solve_cubic(c0: float, c1: float, c2: float, c3: float) -> tuple[int, list[float]]:
        o: list[float] = [0.0] * 5
        
        nr: int = 0
        floatsmall: float = -1.0e-10
        floatone: float = 1.000001

        if (c3 != 0.0):
            a = c2 / c3
            b = c1 / c3
            c = c0 / c3
            a = a / 3

            p = b / 3 - a * a
            q = (2 * a * a * a - a * b + c) / 2
            d = q * q + p * p * p

            if (d > 0.0):
                t = math.sqrt(d)
                o[0] = float(sqrt3d(-q + t) + sqrt3d(-q - t) - a)

                if ((o[0] >= floatsmall) and (o[0] <= floatone)):
                    return 1, o
                return 0, o
            
            if (d == 0.0):
                t = sqrt3d(-q)
                o[0] = float(2 * t - a)

                if ((o[0] >= floatsmall) and (o[0] <= floatone)):
                    nr += 1
                
                o[nr] = float(-t - a)

                if ((o[nr] >= floatsmall) and (o[nr] <= floatone)):
                    return nr + 1, o
                return nr, o

            phi = math.acos(-q / math.sqrt(-(p * p * p)))
            t = math.sqrt(-p)
            p = math.cos(phi / 3)
            q = math.sqrt(3 - 3 * p * p)
            o[0] = float(2 * t * p - a)

            if ((o[0] >= floatsmall) and (o[0] <= floatone)):
                nr += 1
            o[nr] = float(-t * (p + q) - a)

            if ((o[nr] >= floatsmall) and (o[nr] <= floatone)):
                nr += 1
            o[nr] = float(-t * (p - q) - a)

            if ((o[nr] >= floatsmall) and (o[nr] <= floatone)):
                return nr + 1, o
            return nr, o
        a = c2
        b = c1
        c = c0

        if (a != 0.0):
            # /* Discriminant */
            p = b * b - 4 * a * c;

            if (p > 0):
                p = math.sqrt(p);
                o[0] = float((-b - p) / (2 * a));

                if ((o[0] >= floatsmall) and (o[0] <= floatone)):
                    nr += 1
                o[nr] = float((-b + p) / (2 * a));

                if ((o[nr] >= floatsmall) and (o[nr] <= floatone)):
                    return nr + 1, o
                return nr, o

            if (p == 0):
                o[0] = float(-b / (2 * a));
                if ((o[0] >= floatsmall) and (o[0] <= floatone)):
                    return 1, o
            return 0, o

        if (b != 0.0):
            o[0] = float(-c / b);

            if ((o[0] >= floatsmall) and (o[0] <= floatone)):
                return 1, o
            return 0, o

        if (c == 0.0):
            o[0] = 0.0
            return 1, o
        return 0, o

    def berekeny(f1: float, f2: float, f3: float, f4: float, o: list[float]):
        c0 = f1
        c1 = 3.0 * (f2 - f1)
        c2 = 3.0 * (f1 - 2.0 * f2 + f3)
        c3 = f4 - f1 + 3.0 * (f2 - f3)
        return c0 + o[0] * c1 + o[0] * o[0] * c2 + o[0] * o[0] * o[0] * c3
    
    def findzero(x, q0, q1, q2, q3):
        c0 = q0 - x
        c1 = 3.0 * (q1 - q0)
        c2 = 3.0 * (q0 - 2.0 * q1 + q2)
        c3 = q3 - q0 + 3.0 * (q1 - q2)

        return solve_cubic(c0, c1, c2, c3)

    def BKE_fcurve_correct_bezpart( v1: list[float,float],  v2: list[float,float],  v3: list[float,float],  v4: list[float,float]):
        h1 = [0.0, 0.0]
        h2 = [0.0, 0.0]

        len1, len2, len0, fac

        # /* Calculate handle deltas. */
        h1[0] = v1[0] - v2[0]
        h1[1] = v1[1] - v2[1]

        h2[0] = v4[0] - v3[0]
        h2[1] = v4[1] - v3[1]

        # /* Calculate distances:
        # * - len  = Span of time between keyframes.
        # * - len1 = Length of handle of start key.
        # * - len2 = Length of handle of end key.
        # */
        len0 = v4[0] - v1[0]
        len1 = abs(h1[0])
        len2 = abs(h2[0])

        # /* If the handles have no length, no need to do any corrections. */
        if ((len1 + len2) == 0.0):
            return v1, v2, v3 , v4

        # /* To prevent looping or rewinding, handles cannot
        # * exceed the adjacent key-frames time position. */
        if (len1 > len0):
            fac = len0 / len1
            v2[0] = (v1[0] - fac * h1[0])
            v2[1] = (v1[1] - fac * h1[1])

        if (len2 > len0):
            fac = len0 / len2
            v3[0] = (v4[0] - fac * h2[0])
            v3[1] = (v4[1] - fac * h2[1])
        return v1, v2, v3 , v4
    
    # # /* Bezier interpolation. */
    # # /* (v1, v2) are the first keyframe and its 2nd handle. */
    # v1[0] = prevbezt->vec[1][0];
    # v1[1] = prevbezt->vec[1][1];
    # v2[0] = prevbezt->vec[2][0];
    # v2[1] = prevbezt->vec[2][1];
    # # /* (v3, v4) are the last keyframe's 1st handle + the last keyframe. */
    # v3[0] = bezt->vec[0][0];
    # v3[1] = bezt->vec[0][1];
    # v4[0] = bezt->vec[1][0];
    # v4[1] = bezt->vec[1][1];
    # # /* Adjust handles so that they don't overlap (forming a loop). */

    # v1, v2, v3 , v4 = BKE_fcurve_correct_bezpart(v1, v2, v3, v4)

    # /* Try to get a value for this position - if failure, try another set of points. */
    zero, opl = findzero(point, v1[0], v2[0], v3[0], v4[0])
    if zero == 0: 
        return 0.0
    else:
        return berekeny(v1[1], v2[1], v3[1], v4[1], opl)

init_structs()

if __name__ == "__main__":
    
    # Important. This sets up the struct fields.

    win = wmWindow(bpy.context.window)

    for handle in win.modalhandlers:
        if handle.type == WM_HANDLER_TYPE_OP:
            print("Modal running")
            break
    else:
        print("No running modals")
