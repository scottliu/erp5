"""
Export the web page and its components to a single (m)html file.

`format` parameter could also be "mhtml".

TODO: export same components into one mhtml attachment if possible.
"""

from zExceptions import Unauthorized
from base64 import b64encode, b64decode
portal = context.getPortalObject()

mhtml_message = {
  "subtype": "related",
  "param_list": [("type", "text/html")],
  "header_dict": {"From": "<Saved by ERP5>", "Subject": "Untitled"},
  "attachment_list": [],
}

def main():
  data = context.getTextContent("").decode("utf-8")
  data = "".join([fn(p) for fn, p in handleHtmlPartList(parseHtml(data))])
  if format == "mhtml":
    mhtml_message["header_dict"]["Subject"] = context.getTitle() or "Untitled"
    mhtml_message["attachment_list"].insert(0, {
      "mime_type": "text/html",
      "encode": "quoted-printable",
      "add_header_list": [("Content-Location", context.absolute_url())],
      "data": str(data.encode("utf-8")),
    })
    res = context.Base_formatAttachmentListToMIMEMultipartString(**mhtml_message)
    if REQUEST is not None:
      REQUEST.RESPONSE.setHeader("Content-Type", "multipart/related")
      REQUEST.RESPONSE.setHeader("Content-Disposition", 'attachment;filename="%s-%s-%s.mhtml"' % (
        context.getReference("untitled").replace('"', '\\"'),
        context.getVersion("001").replace('"', '\\"'),
        context.getLanguage("en").replace('"', '\\"'),
      ))
    return res
  if REQUEST is not None:
    REQUEST.RESPONSE.setHeader("Content-Type", "text/html")
    REQUEST.RESPONSE.setHeader("Content-Disposition", 'attachment;filename="%s-%s-%s.html"' % (
      context.getReference("untitled").replace('"', '\\"'),
      context.getVersion("001").replace('"', '\\"'),
      context.getLanguage("en").replace('"', '\\"'),
    ))
  return data

def handleHtmlTag(tag, attrs):
  #if tag == "base": and "href" in attrs:  # should not exist in safe-html
  #  NotImplemented
  if tag == "object":
    for i in range(len(attrs)):
      if attrs[i][0] == "data":
        attrs[i] = attrs[i][0], handleImageSource(attrs[i][1])
  elif tag == "img":
    for i in range(len(attrs)):
      if attrs[i][0] == "src":
        attrs[i] = attrs[i][0], handleImageSource(attrs[i][1])
  elif tag == "link" and anny(attrs, key=lambda a: a[0] == "rel" and a[1] == "stylesheet"):
    for i in range(len(attrs)):
      if attrs[i][0] == "href":
        attrs[i] = attrs[i][0], replaceFromDataUri(handleCssHref(attrs[i][1]), replaceCssUrl)
  elif tag == "script":
    for i in range(len(attrs)):
      if attrs[i][0] == "src":
        attrs[i] = attrs[i][0], handleJsSource(attrs[i][1])
  else:
    for i in range(len(attrs)):
      if attrs[i][0] == "href" or attrs[i][0] == "src":
        attrs[i] = attrs[i][0], makeHrefAbsolute(attrs[i][1])
  return tag, attrs

def strHtmlPart(part):
  part_type = part[0]
  if part_type in ("starttag", "startendtag"):
    tag, attrs = handleHtmlTag(part[1], part[2])
    attrs_str = " ".join(["%s=\"%s\"" % (escapeHtml(k), escapeHtml(v or "")) for k, v in attrs])
    return "<%s%s%s>" % (tag, " " + attrs_str if attrs_str else "", " /" if part_type == "startendtag" else "")
  if part_type == "endtag":
    return "</%s>" % part[1]
  if part_type == "data":
    return part[1]
  if part_type == "entityref":
    return "&%s;" % part[1]
  if part_type == "charref":
    return "&#%s;" % part[1]
  if part_type == "comment":
    return "<!--%s-->" % part[1]
  if part_type in ("decl", "unknown_decl"):
    return "<!%s>" % part[1]
  if part_type == "pi":
    return "<?%s>" % part[1]

disallow_script = not allow_script
def handleHtmlPartList(part_list):
  res = []
  style_data = ""
  on_script = False
  on_style = False
  for part in part_list:
    if on_script:
      if part[0] == "endtag" and part[1] == "script":
        on_script = False
      # can only be data until </script> endtag
    elif on_style:
      if part[0] == "endtag" and part[1] == "style":
        res.append((replaceCssUrl, style_data))
        res.append((strHtmlPart, part))
        style_data = ""
        on_style = False
      else:
        # can only be data until </style> endtag
        style_data += strHtmlPart(part)
    else:
      if part[0] == "starttag":
        # when you save a page from a browser, every script tag are removed
        if part[1] == "script" and disallow_script:
          on_script = True
          continue
        elif part[1] == "style":
          on_style = True
      res.append((strHtmlPart, part))
  return res

def handleCssHref(href):
  return handleHref(href)

def handleJsSource(href):
  return handleHref(href)

def handleHref(href):
  if not isHrefAUrl(href):
    return href
  try:
    obj = traverseHref(href)
  except (KeyError, Unauthorized):
    return makeHrefAbsolute(href)
  return handleHrefObject(obj, href)

def handleImageSource(src):
  if not isHrefAUrl(src):
    return src
  try:
    obj = traverseHref(src)
  except (KeyError, Unauthorized):
    return makeHrefAbsolute(src)
  return handleImageSourceObject(obj, src)

def replaceCssUrl(data):
  parts = context.Base_parseCssForUrl(data)
  data = ""
  for part in parts:
    if part[0] == "url":
      url = part[2]
      if isHrefAUrl(url):
        data += handleImageSource(url)
      else:
        data += part[1]
    else:
      data += part[1]
  return data

def handleImageSourceObject(obj, src):
  if hasattr(obj, "convert"):
    search = parseUrlSearch(extractUrlSearch(src))
    format_kw = {}
    for key, value in search:
      if key == "format" and value is not None:
        format_kw["format"] = value
      elif key == "display" and value is not None:
        format_kw["display"] = value
    if format_kw:
      mime, data = obj.convert(**format_kw)
      return handleLinkedData(mime, str(data), src)

  return handleHrefObject(obj, src, default_mimetype=bad_image_mime_type, default_data=bad_image_data)

def handleHrefObject(obj, src, default_mimetype="text/html", default_data="<p>Linked page not found</p>"):
  # handle File portal_skins/folder/file.png
  # XXX handle "?portal_skin=" parameter ?
  if hasattr(obj, "getContentType"):
    mime = obj.getContentType()
    if mime:
      data = getattr(obj, "getData", lambda: str(obj))() or ""
      if isinstance(data, unicode):
        data = data.encode("utf-8")
      return handleLinkedData(mime, data, src)
    return handleLinkedData(default_mimetype, default_data, src)

  # handle Object.view
  # XXX handle url query parameters ? Not so easy because we need to
  # use the same behavior as when we call a script from browser URL bar.
  if not hasattr(obj, "getPortalType") and callable(obj):
    mime, data = "text/html", obj()
    if isinstance(data, unicode):
      data = data.encode("utf-8")
    return handleLinkedData(mime, data, src)

  return handleLinkedData(default_mimetype, default_data, src)

bad_image_data_url = (
  "data:image/png;base64," +  # little image showing cannot load image
  "iVBORw0KGgoAAAANSUhEUgAAABEAAAATCAIAAAD5x3GmAAACWklEQVQokZWSX0hTcRTHz/" +
  "3TunMmMyxrQUzEPQSCFEI0fCi0HmSKdsUGg3q2h5I99dj7bE8Nw6cwLDb3kO7JP5m6h0TE" +
  "CmYQjJYgpaPc7q67+93de04P0zvnQ+CP78Pvdzgfzjnf3+GICE55+NMCACACACKOj49rmv" +
  "afvNHRUZ4/KkBEjLFQKJRTjXyRTqigUSwWI6JQKGSaJhEREQ8ApmkCgFrif+8bJ7RfMAGA" +
  "MRYMBsPhMCLWzFPUUdVI1cjjEj0usXLXdLJ6sTCx2jIBAd1otVVe11vPbKT1iqeJRMLKKp" +
  "fLVYaoChxGEAwDbt0ZsNs4ABAEbiLyoqYOEax/ZyfsYmX4q5iCAABQd1aoen3UGmDt/zod" +
  "/EWnuJczcgcIABzHu91um81W9YCI8Jga6rirqUV41O9pQqeDR6J6iRvs7VUeDFQZJCKEih" +
  "DxfINemIioq4ms7GtrwkaH4KovZ2WfujLL1/SGiIgZZSmavj2Veto0GYXO7vzawo7saztX" +
  "3JF9+bUF6Oyu8YAAtnLvNrJBAOPb7lbkizQyPZuWfX8+LeTaG00NHDe7r8Rmju0oQaawVA" +
  "Eqga+/Xkc+B1vexDSJzx+AJvEtk1FDEHjLAEXfXdt7ZgEA0H754UjH2GZgWFGR2UVFxc3A" +
  "sIh4yDDGFjPPdfxhAdea/Y87xpJy//bqnN3b05XK2r0928n55P2+w3kMw9CXmy/AE4u5Fw" +
  "h89A/tLM9d6urxTr9/G4/74zMfBvt+rsxzRKTruqIojNUsgSRJB+vrqVcv705Fc8ViqVSS" +
  "JMnpcMz5h/4B1Qxz9NOjZCgAAAAASUVORK5CYII="
)
bad_image_data = b64decode(bad_image_data_url.split(",", 1)[1])
bad_image_mime_type = "image/png"

request_protocol = context.REQUEST.SERVER_URL.split(":", 1)[0] + ":"
site_object_dict = context.ERP5Site_getWebSiteDomainDict()
base_url_root_object = getattr(context, "getWebSiteValue", str)() or portal
base_url_object = context
assert base_url_object.getRelativeUrl().startswith(base_url_root_object.getRelativeUrl())
base_url = base_url_object.getRelativeUrl()[len(base_url_root_object.getRelativeUrl()):]
if not base_url.startswith("/"):
  base_url = "/" + base_url

def handleLinkedData(mime, data, href):
  if format == "mhtml":
    url = makeHrefAbsolute(href)
    mhtml_message["attachment_list"].append({
      "mime_type": mime,
      "encode": "quoted-printable" if mime.startswith("text/") else None,
      "add_header_list": [("Content-Location", url)],
      "data": str(data),
    })
    return url
  else:
    return "data:%s;base64,%s" % (mime, b64encode(data))

def makeHrefAbsolute(href):
  if isHrefAnAbsoluteUrl(href) or not isHrefAUrl(href):
    return href
  if href.startswith("//"):
    return request_protocol + href
  if href.startswith("/"):
    return base_url_root_object.absolute_url() + href
  return base_url_object.absolute_url() + "/" + href

def isHrefAnAbsoluteUrl(href):
  return href.startswith("https://") or href.startswith("http://")

def isHrefAUrl(href):
  return href.startswith("https://") or href.startswith("http://") or not href.split(":", 1)[0].isalpha()

normalize_kw = {"keep_empty": False, "keep_trailing_slash": False}
def traverseHref(url, allow_hash=False):
  url = url.split("?")[0]
  if not allow_hash:
    url = url.split("#")[0]
  if url.startswith("https://") or url.startswith("http://") or url.startswith("//"):  # absolute url possibly on other sites
    site_url = "/".join(url.split("/", 3)[:3])
    domain = url.split("/", 3)[2]
    site_object = site_object_dict[domain]
    relative_path = url[len(site_url):]
    relative_path = (relative_path[1:] if relative_path[:1] == "/" else relative_path)
    relative_path = context.Base_normalizeUrlPathname("/" + relative_path, **normalize_kw)[1:]
    return site_object.restrictedTraverse(str(relative_path))
  if url.startswith("/"):  # absolute path, relative url
    return base_url_root_object.restrictedTraverse(str(context.Base_normalizeUrlPathname(url, **normalize_kw)[1:]))
  # relative url
  return base_url_root_object.restrictedTraverse(str(context.Base_normalizeUrlPathname(base_url + "/" + url, **normalize_kw)[1:]))

def replaceFromDataUri(data_uri, replacer):
  header, data = data_uri.split(",")
  if "text/css" not in header:
    return data_uri
  is_base64 = False
  if ";base64" in header:
    is_base64 = True
    data = b64decode(data)
  data = replacer(data)
  return "%s,%s" % (header, b64encode(data) if is_base64 else data)

def extractUrlSearch(url):
  url = url.split("#", 1)[0].split("?", 1)
  url[0] = ""
  return "?".join(url)

def parseUrlSearch(search):
  if search[:1] == "?":
    search = search[1:]
  result = []
  for part in search.split("&"):
    key = part.split("=")
    value = "=".join(key[1:]) if len(key) else None
    result.append((key[0], value))
  return result

def parseHtml(text):
  return context.Base_parseHtml(text)

def escapeHtml(text):
  return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\"", "&quot;")

def anny(iterable, key=None):
  for i in iterable:
    if key:
      i = key(i)
    if i:
      return True
  return False

return main()
