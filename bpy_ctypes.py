#!/usr/bin/env python3

import bpy
from ctypes import *
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
# source/blender/editors/include/ED_numinput.hh
class NumInput(StructBase):
    idx_max: c_short
    unit_sys: c_int
    unit_type: c_int  * NUM_MAX_ELEMENTS
    unit_use_radians: c_bool
    flag: c_short
    val_flag: c_short  * NUM_MAX_ELEMENTS
    val: c_float  * NUM_MAX_ELEMENTS
    val_org: c_float  * NUM_MAX_ELEMENTS
    val_inc: c_float  * NUM_MAX_ELEMENTS
    idx: c_short
    str_: c_char * NUM_STR_REP_LEN
    str_cur: c_int

# /source/blender/windowmanager/intern/wm_operators.cc
class RadialControl(StructBase):
    type: c_int # PropertyType 
    subtype: c_int # PropertySubType 
    ptr: PointerRNA 
    col_ptr: PointerRNA 
    fill_col_ptr: PointerRNA 
    rot_ptr: PointerRNA 
    zoom_ptr: PointerRNA 
    image_id_ptr: PointerRNA
    fill_col_override_ptr: PointerRNA 
    fill_col_override_test_ptr: PointerRNA
    prop: lambda: POINTER(PropertyRNA)
    col_prop: lambda: POINTER(PropertyRNA)
    fill_col_prop: lambda: POINTER(PropertyRNA)
    rot_prop: lambda: POINTER(PropertyRNA)
    zoom_prop: lambda: POINTER(PropertyRNA)
    fill_col_override_prop: lambda: POINTER(PropertyRNA)
    fill_col_override_test_prop: lambda: POINTER(PropertyRNA)
    image_id_srna: lambda: POINTER(StructRNA)
    initial_value: c_float 
    current_value: c_float 
    min_value: c_float 
    max_value: c_float
    initial_mouse: c_int * 2
    initial_co: c_int * 2
    slow_mouse: c_int * 2
    slow_mode: c_bool
    scale_fac: c_float
    dial: c_void_p # Dial
    texture: c_void_p # GPUTexture
    orig_paintcursors: ListBase
    use_secondary_tex: c_bool
    cursor: c_void_p
    num_input: NumInput
    init_event: c_int

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

# /source/blender/editors/transform/transform.hh

class TransCon(StructBase):
    text: c_char * 50
    pmtx: (c_float * 3) * 3
    mode: c_int # eTConstraint
    drawExtra: c_void_p
    # void (*drawExtra)(TransInfo *t);
    applyVec: c_void_p
    # void (*applyVec)(const TransInfo *t,
    #                 const TransDataContainer *tc,
    #                 const TransData *td,
    #                 const float in[3],
    #                 float r_out[3]);
    applySize: c_void_p
    # void (*applySize)(const TransInfo *t,
    #                 const TransDataContainer *tc,
    #                 const TransData *td,
    #                 float r_smat[3][3]);
    applyRot: c_void_p
    # void (*applyRot)(const TransInfo *t,
    #                 const TransDataContainer *tc,
    #                 const TransData *td,
    #                 float r_axis[3],
    #                 float *r_angle);

# /source/blender/editors/transform/transform.hh
class TransSnap(StructBase):
    flag: c_int # enum eSnapFlag
    mode: c_int # enum eSnapMode
    source_operation: c_int # enum eSnapSourceOP
    target_operation: c_int # enum eSnapTargetOP
    face_nearest_steps: c_short
    status: c_int # enum eTSnap
    source_type: c_int # enum eSnapMode
    target_type: c_int # enum eSnapMode
    snap_source: c_float * 3
    snap_target: c_float * 3
    snapNormal: c_float * 3
    snapNodeBorder: c_char
    points: ListBase
    selectedPoint: c_void_p # TransSnapPoint *
    last: c_double
    snap_target_fn: c_void_p # void (*snap_target_fn)(TransInfo *, float *);
    snap_source_fn: c_void_p # void (*snap_source_fn)(TransInfo *);
    # union {
    # SnapObjectContext *object_context;
    # TransSeqSnapData *seq_context;
    # };
    seq_context: c_void_p
# /source/blender/editors/transform/transform.hh

class MouseInput(StructBase):
    apply: c_void_p # void (*apply)(TransInfo *t, MouseInput *mi, const double mval[2], float output[3]);
    post: c_void_p # void (*post)(TransInfo *t, float values[3]);
    imval: c_float * 2 # blender::float2 
    center: c_float * 2 # blender::float2 
    factor: c_float
    precision_factor: c_float
    precision: c_bool
    data: c_void_p
    use_virtual_mval: c_bool
    class virtual_mval(StructBase):
        prev: c_double * 2
        accum: c_double * 2
    virtual_mval : virtual_mval

# /source/blender/editors/transform/transform.hh

class TransCustomData(StructBase):
    data: c_void_p # void *data;
    free_cb: c_void_p # void (*free_cb)(TransInfo *, TransDataContainer *tc, TransCustomData *custom_data);
    use_free : c_uint

class TransCustomDataContainer(StructBase):
#   union {
#     TransCustomData mode, first_elem;
#   };
    mode: TransCustomData
    type: TransCustomData


class TransInfo(StructBase):
    data_container: c_void_p # TransDataContainer
    data_container_len: c_int
    data_len_all: c_int
    data_type: c_void_p # TransConvertTypeInfo
    mode: c_int # enum eTfmMode
    mode_info: c_void_p # TransModeInfo
    options: c_int # enum eTContext
    flag: c_int # enum eTFlag
    modifiers: c_int # enum eTModifier
    state: c_int # enum eTState
    redraw: c_int # enum eRedrawFlag
    helpline: c_int # enum eTHelpline
    con: TransCon
    tsnap: TransSnap
    num: NumInput
    mouse: MouseInput
    prop_size: c_float
    proptext: c_char * 20
    aspect: c_float * 3
    center_global: c_float * 3
    center2d: c_float * 2
    idx_max: c_short
    snap: c_float * 2
    snap_spatial: c_float * 3
    snap_spatial_precision: c_float
    viewmat: (c_float * 4) * 4
    viewinv: (c_float * 4) * 4
    persmat: (c_float * 4) * 4
    persinv: (c_float * 4) * 4
    persp: c_short
    around: c_short
    spacetype: c_char
    obedit_type: c_short
    vec: c_float * 3
    mat: (c_float * 3) * 3
    spacemtx: (c_float * 3) * 3
    spacemtx_inv: (c_float * 3) * 3
    spacename: c_char * 64
    launch_event: c_short
    is_launch_event_drag: c_bool
    is_orient_default_overwrite: c_bool

    class orient(StructBase):
        type: c_short
        matrix: (c_float * 3) * 3

    orient: orient * 3

    orient_curr: c_int # enum eTOType
    orient_type_mask: c_int
    prop_mode: c_short
    values: c_float * 4
    values_modal_offset: c_float * 4
    values_final: c_float * 4
    values_inside_constraints: c_float * 4
    orient_axis: c_int
    orient_axis_ortho: c_int
    remove_on_cancel: c_bool
    view: c_void_p # void
    context: c_void_p # bContext
    mbus: c_void_p # wmMsgBus
    area: c_void_p # ScrArea
    region: c_void_p # ARegion
    depsgraph: c_void_p # Depsgraph
    scene: c_void_p # Scene
    view_layer: c_void_p # ViewLayer
    settings: c_void_p # ToolSettings
    animtimer: c_void_p # wmTimer
    keymap: c_void_p # wmKeyMap
    reports: c_void_p # ReportList
    mval: c_float * 2 # blender::float2
    zfac: c_float
    draw_handle_view: c_void_p # void
    draw_handle_pixel: c_void_p # void
    draw_handle_cursor: c_void_p # void
    rng: c_void_p # RNG
    vod: c_void_p # ViewOpsData
    custom: TransCustomDataContainer
    undo_name: c_char_p


# /source/blender/makesdna/DNA_session_uid_types.h

class SessionUID(StructBase):
    uid_: c_uint64

# /source/blender/makesdna/DNA_sequence_types.h

class SequenceRuntime(StructBase):
    session_uid: SessionUID

# blender/source/blender/makesdna/DNA_color_types.h

class ColorManagedColorspaceSettings(StructBase):
    name: c_char * 64

class Strip(StructBase):
    next: lambda: POINTER(Strip)
    prev: lambda: POINTER(Strip)
    us: c_int 
    done: c_int
    startstill: c_int 
    endstill: c_int
    # /**
    # * Only used as an array in IMAGE sequences(!),
    # * and as a 1-element array in MOVIE sequences,
    # * NULL for all other strip-types.
    # */
    stripdata: c_void_p # StripElem
    dirpath: c_char * 768
    proxy: c_void_p # StripProxy
    crop: c_void_p # StripCrop
    transform: c_void_p # StripTransform
    color_balance: c_void_p # StripColorBalance DNA_DEPRECATED;
    colorspace_settings: ColorManagedColorspaceSettings


class Sequence(StructBase):
    next: lambda: POINTER(Sequence)
    prev: lambda: POINTER(Sequence)
    tmp: c_void_p
    lib: c_void_p
    name: c_char * 64
    flag: c_int
    type: c_int
    len: c_int
    start: c_float
    startofs: c_float
    endofs: c_float
    startstill: c_float
    endstill: c_float
    machine: c_int
    _pad: c_int
    startdisp: c_int
    enddisp: c_int
    sat: c_float
    mul: c_float
    _pad1: c_float
    anim_preseek: c_short
    streamindex: c_short
    multicam_source: c_int
    clip_flag: c_int
    strip: lambda: POINTER(Strip)
    ipo: c_void_p # struct Ipo
    scene: c_void_p # struct Scene
    scene_camera: c_void_p # struct Object
    clip: c_void_p # struct MovieClip
    mask: c_void_p # struct Mask
    anims: ListBase
    effect_fader: c_float
    speed_fader: c_float
    seq1: lambda: POINTER(Sequence)
    seq2: lambda: POINTER(Sequence)
    seq3: lambda: POINTER(Sequence)
    seqbase: ListBase
    channels: ListBase
    sound: c_void_p # struct bSound
    scene_sound: c_void_p
    volume: c_float
    pitch: c_float # DNA_DEPRECATED, 
    pan: c_float
    strobe: c_float
    effectdata: c_void_p
    anim_startofs: c_int
    anim_endofs: c_int
    blend_mode: c_int
    blend_opacity: c_float
    color_tag: c_int8
    alpha_mode: c_char
    _pad2: c_char * 2
    cache_flag: c_int
    sfra: c_int
    views_format: c_char
    _pad3: c_char * 3
    stereo3d_format: c_void_p # Stereo3dFormat
    prop: lambda: POINTER(IDProperty)
    modifiers: ListBase
    media_playback_rate: c_float
    speed_factor: c_float
    retiming_keys: c_void_p # struct SeqRetimingKey
    _pad5: c_void_p
    retiming_keys_num: c_int
    _pad6: c_char * 4
    runtime: SequenceRuntime

# source/blender/makesdna/DNA_vec_types.h

class rctf(StructBase): 
  xmin: c_float
  xmax: c_float
  ymin: c_float
  ymax: c_float


# /source/blender/makesdna/DNA_sequence_types.h

class EditingRuntime(StructBase):
    sequence_lookup: c_void_p # struct SequenceLookup
    media_presence: c_void_p # MediaPresence

class Editing(StructBase):
    seqbasep: lambda: POINTER(ListBase)
    displayed_channels: lambda: POINTER(ListBase)
    _pad0: c_void_p
    seqbase: ListBase
    metastack: ListBase
    channels: ListBase
    act_seq: lambda: POINTER(Sequence)
    act_imagedir: c_char * 1024
    act_sounddir: c_char * 1024
    proxy_dir: c_char * 1024
    proxy_storage: c_int
    overlay_frame_ofs: c_int 
    overlay_frame_abs: c_int
    overlay_frame_flag: c_int
    overlay_frame_rect: rctf
    show_missing_media_flag: c_int
    _pad1: c_int
    cache: c_void_p # struct SeqCache
    recycle_max_cost: c_float #/* UNUSED only for versioning. */
    cache_flag: c_int
    prefetch_job: c_void_p # struct PrefetchJob *
    disk_cache_timestamp: c_int64
    runtime: EditingRuntime

# source/blender/makesdna/DNA_view3d_types.h
class View3DCursor(StructBase):
    location: c_float * 3
    rotation_quaternion: c_float * 4
    rotation_euler: c_float * 3
    rotation_axis: c_float * 3
    rotation_angle: c_float
    rotation_mode: c_short
    _pad: c_char * 6

# # source/blender/makesdna/DNA_scene_types.h
class Scene(StructBase):
    id: ID
    # /** Animation data (must be immediately after id for utilities to use it). */
    adt: c_void_p # struct AnimData *
    # /**
    # * Engines draw data, must be immediately after AnimData. See IdDdtTemplate and
    # * DRW_drawdatalist_from_id to understand this requirement.
    # */
    drawdata: ListBase # DrawDataList
    camera: c_void_p # struct Object
    world: c_void_p # struct World
    set: c_void_p # struct Scene
    base: ListBase # DNA_DEPRECATED;
    # /** Active base. */
    basact: c_void_p # struct Base * DNA_DEPRECATED;
    _pad1: c_void_p
    # /** 3d cursor location. */
    cursor: View3DCursor
    # /** Bit-flags for layer visibility (deprecated). */
    lay: c_uint # DNA_DEPRECATED;
    # /** Active layer (deprecated). */
    layact: c_int # DNA_DEPRECATED;
    _pad2: c_char * 4
    # /** Various settings. */
    flag: c_short
    use_nodes: c_char
    _pad3: c_char * 1
    nodetree: c_void_p # struct bNodeTree
    # /** Sequence editor data is allocated here. */
    ed: lambda: POINTER(Editing)
    # /** Default allocated now. */
    # toolsettings: c_void_p # struct ToolSettings
    # _pad4: c_void_p
    # safe_areas: DisplaySafeAreas
    # # /* Migrate or replace? depends on some internal things... */
    # # /* No, is on the right place (ton). */
    # r: RenderData
    # audio: AudioData
    # markers: ListBase
    # transform_spaces: ListBase
    # # /** First is the [scene, translate, rotate, scale]. */
    # orientation_slots: TransformOrientationSlot * 4
    # sound_scene: c_void_p
    # playback_handle: c_void_p
    # sound_scrub_handle: c_void_p
    # speaker_handles: c_void_p
    # # /** (runtime) info/cache used for presenting playback frame-rate info to the user. */
    # fps_info: c_void_p
    # depsgraph_hash: c_void_p # struct GHash
    # _pad7: c_char * 4
    # active_keyingset: c_int
    # keyingsets: ListBase
    # unit: UnitSettings
    # gpd: c_void_p # struct bGPdata
    # clip: c_void_p # struct MovieClip
    # physics_settings: PhysicsSettings
    # _pad8: c_void_p
    # customdata_mask: CustomData_MeshMasks
    # customdata_mask_modal: CustomData_MeshMasks
    # view_settings: ColorManagedViewSettings
    # display_settings: ColorManagedDisplaySettings
    # sequencer_colorspace_settings: ColorManagedColorspaceSettings
    # rigidbody_world: c_void_p # struct RigidBodyWorld
    # preview: c_void_p # struct PreviewImage
    # view_layers: ListBase
    # master_collection: c_void_p # struct Collection
    # layer_properties: lambda: POINTER(IDProperty)
    # simulation_frame_start: c_int
    # simulation_frame_end: c_int
    # display: SceneDisplay
    # eevee: SceneEEVEE
    # grease_pencil_settings: SceneGpencil
    # hydra: SceneHydra
    # runtime: c_void_p # SceneRuntimeHandle
    # _pad9: c_void_p


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

def BLI_addtail(listbase, vlink):
    cptr = POINTER(vlink.__class__)
    vlink.next = cptr()
    vlink.prev = cptr(vlink.__class__(listbase.last))
    
    if listbase.last:
        lblast = vlink.__class__(listbase.last)
        lblast.next = cptr(vlink)
    if not listbase.first:
        listbase.first = addressof(vlink)
    listbase.last = addressof(vlink)
    

def BLI_remlink(listbase, vlink):
    if vlink.prev:
        vlink.prev.contents.next = vlink.next
    if vlink.next:
        vlink.next.contents.prev = vlink.prev
    
    if listbase.last == addressof(vlink):
        if vlink.prev:
            listbase.last = addressof(vlink.prev.contents)
        else:
            listbase.last = c_void_p()

    if listbase.first == addressof(vlink):
        if vlink.next:
            listbase.first = addressof(vlink.next.contents)
        else:
            listbase.first = c_void_p()

def get_running_op(window) -> str | None:
    win = wmWindow(window)
    
    for handle in win.modalhandlers:
        if handle.type == WM_HANDLER_TYPE_OP:
            handlec = wmEventHandler_Op(addressof(handle))
            return bytes.decode(handlec.op.contents.type.contents.idname)
    return None
            # old_value = operator_just_ran.old_value
            # if operator_just_ran(idname) and old_value: update_effect_on(old_value, effects)
            # update_effect_on(idname, effects)
            # handled = True
    # if not handled:
    #     old_value = operator_just_ran.old_value
    #     if operator_just_ran(False) and old_value:
    #         update_effect_on(old_value, effects)
    #         pass

def move_sequence(sourcescene, targetscene, sequence):
    sscene = Scene(sourcescene)
    tscene = Scene(targetscene)
    seqsource = Sequence(sequence)

    BLI_remlink(sscene.ed.contents.seqbase, seqsource)
    BLI_addtail(tscene.ed.contents.seqbase, seqsource)

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
