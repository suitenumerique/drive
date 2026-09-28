// Runs on "01 list root items". Resets the browse variables so a skipped
// "04 open folder" step cannot leave a stale subfolder id from a previous
// iteration (browse_folder_id itself is re-extracted on every iteration).
vars.put("browse_subfolder_id", "NONE")
