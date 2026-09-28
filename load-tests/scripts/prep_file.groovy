// Splits the current upfile_N entry ("relative dir" + SEP + "absolute path"
// + SEP + "name", see plan_upload.groovy) and resolves the parent item id
// and mimetype for the file about to be uploaded.
def parts = vars.get("current_upfile").split("\u001F", 3)
def relDir = parts[0]
vars.put("cf_parent", relDir.isEmpty() ? vars.get("folder_id") : vars.get("upfid_" + relDir))
vars.put("cf_abs", parts[1])
vars.put("cf_name", parts[2])
def mime = java.net.URLConnection.guessContentTypeFromName(parts[2])
vars.put("cf_mime", mime ?: "application/octet-stream")
