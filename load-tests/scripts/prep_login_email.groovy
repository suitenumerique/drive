// Resolves the login email for this thread. If the USER_EMAIL property is
// set (-JUSER_EMAIL=someone@example.com), every thread logs in with it;
// otherwise each thread gets a unique generated address based on
// USER_OFFSET + thread number (ctx.getThreadNum() is 0-based, the generated
// names start at 1 to match the documented load-user-1..N scheme).
def email = props.getProperty("USER_EMAIL")
if (email == null || email.trim().isEmpty()) {
    def offset = (props.getProperty("USER_OFFSET") ?: "0") as int
    email = "load-user-" + (offset + ctx.getThreadNum() + 1) + "@test.test"
}
vars.put("login_email", email)
