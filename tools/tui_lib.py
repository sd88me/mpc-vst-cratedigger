"""JSON writer and TUI building blocks shared by the skin generators (copied from the Acid and Welle ports, docs/SDK-PORTING.md)."""

# ---- a JSON writer that keeps key order and allows the overlay widgets' duplicate "version" key ------------------
class Obj:
    """An ordered JSON object that may repeat a key: Obj(("version", 2), ("version", 1), ...)."""
    def __init__(self, *pairs):
        self.pairs = list(pairs)


def dump(v, ind=0):
    sp = "  " * ind
    if hasattr(v, "pairs"):   # Obj from either copy of this module (it is also imported by skin_pages)
        pairs = v.pairs
    elif isinstance(v, dict):
        pairs = list(v.items())
    else:
        pairs = None
    if pairs is not None:
        if not pairs:
            return "{}"
        inner = (",\n").join("%s  %s: %s" % (sp, dump(k), dump(x, ind + 1)) for k, x in pairs)
        return "{\n%s\n%s}" % (inner, sp)
    if isinstance(v, list):
        if not v:
            return "[]"
        return "[\n%s\n%s]" % (",\n".join(sp + "  " + dump(x, ind + 1) for x in v), sp)
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float):
        return repr(v)
    if isinstance(v, int):
        return str(v)
    s = str(v).replace("\\", "\\\\").replace('"', '\\"')
    return '"%s"' % s


# ---- building blocks -----------------------------------------------------------------------------------------------
def bounds(b, focus="No", visible="Always", invalid="Show", ind=None):
    d = {"version": 2 if ind else 1, "acceptsHWFocus": focus, "showWhenDataModelInvalid": invalid, "whenVisible": visible,
         "boundsType": "Absolute", "bounds": b}
    if ind:
        d["additionalInvalidatingHandles"] = ind
    return d


def entry(name, typ, data, b, remap=None, focus="No", visible="Always", ind=None):
    """remap: one parameter (bound to Data) or a list of (handle, parameter) pairs."""
    if isinstance(remap, str):
        remap = [("Data", remap)]
    return {"version": 2,
            "componentData": {"version": 1, "name": name, "type": typ, "data": data},
            "handle remapping": {"version": 1, "map": [{"key": k, "value": v} for k, v in (remap or [])]},
            "bounds": bounds(b, focus, visible, ind=ind)}


def bg(colour="0", image=""):
    return {"version": 1, "focussed": {"version": 1, "colour": colour, "image": image},
            "unfocussed": {"version": 1, "colour": colour, "image": image}}


def component(children, actions=None, ignore=False, background=None):
    return {"version": 2, "actions": actions or [], "backgroundData": background or bg(),
            "ignoreMousePresses": ignore, "disableCoarseDataWheel": False, "componentsData": children}


def act(on, handler, extra=""):
    return {"version": 1, "onAction": on, "handler": handler, "handleName": "Data", "additionalData": extra}


FOCUS = {"version": 1, "backgroundColour": "19ffffff", "outlineColour": "ffe81f40", "backgroundInset": 4.0, "outlineThickness": 1.0}


def text_style(h=22.0, colour="ffbea880", style="SemiBold", just="left verticallyCentred", case="Upper Case", font="Titillium Web"):
    return {"version": 1, "font": {"version": 1, "name": font, "style": style, "height": h}, "colour": colour,
            "justification": just, "case": case}


def label(kind, b, remap=None, text=None, **ts):
    d = {"version": 1, "textStyle": text_style(**ts), "type": kind, "handleName": "Data" if remap else "Invalid"}
    if text is not None:
        d["text"] = text
    return entry("label", "Label", d, b, remap)


def _inherit(e):
    """A label inside a component reads the component's own Data handle."""
    e["componentData"]["data"]["handleName"] = "Data"
    return e


