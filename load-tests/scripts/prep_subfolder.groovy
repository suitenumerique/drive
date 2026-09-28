// Computes the parent item id and the title for the subfolder being created.
// current_updir holds a relative path like "mon_dossier/1er Janvier 2024";
// its parent is either the iteration root folder (single segment) or an
// already-created subfolder whose id was stored under "upfid_<parent path>".
def rel = vars.get("current_updir")
def slash = rel.lastIndexOf("/")
if (slash == -1) {
    vars.put("cdir_parent", vars.get("folder_id"))
    vars.put("cdir_title", rel)
} else {
    vars.put("cdir_parent", vars.get("upfid_" + rel.substring(0, slash)))
    vars.put("cdir_title", rel.substring(slash + 1))
}
