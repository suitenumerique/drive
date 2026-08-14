// Stores the id of the subfolder just created so that its children (folders
// and files) can reference it as parent.
vars.put("upfid_" + vars.get("current_updir"), vars.get("cdir_id"))
