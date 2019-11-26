import MKService

import machinetalk.protobuf.preview_pb2 as PREVIEW

class Preview(object):
    def __init__(self, container):
        self.type = container.type
        self.container = container

class PreviewPosition(object):
    def __init__(self, container):
        Preview.__init__(self, container)
        self.x = container.x
        self.y = container.y
        self.z = container.z
        self.a = container.a
        self.b = container.b
        self.c = container.c
        self.u = container.u
        self.v = container.v
        self.w = container.w

class PreviewStart(Preview):
    def __init__(self, container):
        Preview.__init__(self, container)

class PreviewSetG5xOffset(Preview):
    def __init__(self, container):
        Preview.__init__(self, container)

class PreviewSetG92Offset(Preview):
    def __init__(self, container):
        Preview.__init__(self, container)

class PreviewSetXYRotation(Preview):
    def __init__(self, container):
        Preview.__init__(self, container)

class PreviewSourceContext(Preview):
    def __init__(self, container):
        Preview.__init__(self, container)

class PreviewSetParams(Preview):
    def __init__(self, container):
        Preview.__init__(self, container)

class PreviewSetFeedMode(Preview):
    def __init__(self, container):
        Preview.__init__(self, container)

class PreviewComment(Preview):
    def __init__(self, container):
        Preview.__init__(self, container)

class PreviewMessage(Preview):
    def __init__(self, container):
        Preview.__init__(self, container)

class PreviewSelectPlane(Preview):
    def __init__(self, container):
        Preview.__init__(self, container)

class PreviewUseToolOffset(Preview):
    def __init__(self, container):
        Preview.__init__(self, container)

class PreviewChangeTool(Preview):
    def __init__(self, container):
        Preview.__init__(self, container)

class PreviewChangeToolNumber(Preview):
    def __init__(self, container):
        Preview.__init__(self, container)

class PreviewStraightTraverse(Preview):
    def __init__(self, container):
        Preview.__init__(self, container)

class PreviewSetFeedRate(Preview):
    def __init__(self, container):
        Preview.__init__(self, container)

class PreviewSetTraverseRate(Preview):
    def __init__(self, container):
        Preview.__init__(self, container)

class PreviewStraightFeed(Preview):
    def __init__(self, container):
        Preview.__init__(self, container)

class PreviewArcFeed(Preview):
    def __init__(self, container):
        Preview.__init__(self, container)

class PreviewDwell(Preview):
    def __init__(self, container):
        Preview.__init__(self, container)

class PreviewStraightProbe(Preview):
    def __init__(self, container):
        Preview.__init__(self, container)

class PreviewRigidTap(Preview):
    def __init__(self, container):
        Preview.__init__(self, container)

class PreviewEnd(Preview):
    def __init__(self, container):
        Preview.__init__(self, container)

_Preview = {
        PREVIEW.PV_STRAIGHT_PROBE     : PreviewStraightProbe,
        PREVIEW.PV_RIGID_TAP          : PreviewRigidTap,
        PREVIEW.PV_STRAIGHT_FEED      : PreviewStraightFeed,
        PREVIEW.PV_ARC_FEED           : PreviewArcFeed,
        PREVIEW.PV_STRAIGHT_TRAVERSE  : PreviewStraightTraverse,
        PREVIEW.PV_SET_G5X_OFFSET     : PreviewSetG5xOffset,
        PREVIEW.PV_SET_G92_OFFSET     : PreviewSetG92Offset,
        PREVIEW.PV_SET_XY_ROTATION    : PreviewSetXYRotation,
        PREVIEW.PV_SELECT_PLANE       : PreviewSelectPlane,
        PREVIEW.PV_SET_TRAVERSE_RATE  : PreviewSetTraverseRate,
        PREVIEW.PV_SET_FEED_RATE      : PreviewSetFeedRate,
        PREVIEW.PV_CHANGE_TOOL        : PreviewChangeTool,
        PREVIEW.PV_CHANGE_TOOL_NUMBER : PreviewChangeToolNumber,
        PREVIEW.PV_DWELL              : PreviewDwell,
        PREVIEW.PV_MESSAGE            : PreviewMessage,
        PREVIEW.PV_COMMENT            : PreviewComment,
        PREVIEW.PV_USE_TOOL_OFFSET    : PreviewUseToolOffset,
        PREVIEW.PV_SET_PARAMS         : PreviewSetParams,
        PREVIEW.PV_SET_FEED_MODE      : PreviewSetFeedMode,
        PREVIEW.PV_SOURCE_CONTEXT     : PreviewSourceContext,
        PREVIEW.PV_PREVIEW_START      : PreviewStart,
        PREVIEW.PV_PREVIEW_END        : PreviewEnd,
        }

def CreatePreview(container):
    return _Preview[container.type](container)

class MKServicePreview(MKService.MKServiceSubscribe):

    def __init__(self, context, name, properties):
        MKService.MKServiceSubscribe.__init__(self, context, name, properties)
        self.preview = []
        self.complete = False

    def topicNames(self):
        return ['preview']

    def topicName(self):
        return 'preview'

    def process(self, container):
        preview = []
        for pc in container.preview:
            p = CreatePreview(pc)
            if PreviewStart == type(p):
                self.preview = []
                self.complete = False
            if PreviewEnd == type(p):
                self.complete = True
            preview.append(p)
        self.preview.extend(preview)
        #print('preview', self.complete, len(self.preview))
        if self.complete:
            self.notifyObservers(len(self.preview))

class MKServicePreviewStatus(MKService.MKServiceSubscribe):

    def __init__(self, context, name, properties):
        MKService.MKServiceSubscribe.__init__(self, context, name, properties)
        self.interp_state = None
        self.note = []

    def topicNames(self):
        return ['status']

    def topicName(self):
        return 'previewstatus'

    def process(self, container):
        updated = []
        if container.HasField('interp_state'):
            self.interp_state = container.interp_state
            updated.append('interp_state')
        if container.note:
            self.note = [n for n in container.note]
            updated.append('note')
        #print('previewstatus', self.interp_state, self.note)
        self.notifyObservers(updated)
