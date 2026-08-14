// Picks a random entry (file or folder) from the fixtures directory and
// flattens it into JMeter variables consumed by the two ForEach controllers
// of the "04 upload entry" transaction:
//   updir_1..N  - folder relative paths, parents always before children
//   upfile_1..M - files as "relative dir" + SEP + "absolute path" + SEP + "name"
// This mirrors the frontend folder upload (useUpload.tsx): materialize the
// folder hierarchy first, then upload each file into its created parent.
// This sampler performs no HTTP request and is excluded from the results.
import java.util.concurrent.ThreadLocalRandom
import org.apache.jmeter.services.FileServer

SampleResult.setIgnore()

def fixturesPath = props.getProperty("FIXTURES_DIR", "files")
def fixtures = new File(fixturesPath)
if (!fixtures.isAbsolute()) {
    fixtures = new File(FileServer.getFileServer().getBaseDir(), fixturesPath)
}
def entries = (fixtures.listFiles() ?: new File[0])
        .findAll { !it.name.startsWith(".") }
        .sort { it.name }
if (entries.isEmpty()) {
    throw new IllegalStateException("No fixture entries found in " + fixtures.absolutePath)
}

// Clear the plan of the previous iteration.
["updir_", "upfile_"].each { prefix ->
    def i = 1
    while (vars.get(prefix + i) != null) {
        vars.remove(prefix + i)
        i++
    }
}

// Seed mode (opt-in, used by the read-heavy scenario): on the first
// iteration of each thread, pick a folder entry deterministically so every
// user starts the run with a navigable tree to read from. Scenarios that do
// not define the seed_first_iteration variable keep the random pick.
def entry
if ("true" == vars.get("seed_first_iteration") && vars.getIteration() == 1) {
    entry = entries.find { it.isDirectory() } ?: entries[0]
} else {
    entry = entries[ThreadLocalRandom.current().nextInt(entries.size())]
}
// Unit separator: cannot appear in file names, unlike "|" or ",".
def SEP = "\u001F"
def dirs = []
def files = []

def collect
collect = { File node, String rel ->
    if (node.isDirectory()) {
        dirs << rel
        (node.listFiles() ?: new File[0])
                .findAll { !it.name.startsWith(".") }
                .sort { it.name }
                .each { child -> collect(child, rel + "/" + child.name) }
    } else {
        def relDir = rel.substring(0, rel.lastIndexOf("/"))
        files << [relDir, node.absolutePath, node.name].join(SEP)
    }
}

if (entry.isDirectory()) {
    collect(entry, entry.name)
} else {
    files << ["", entry.absolutePath, entry.name].join(SEP)
}

dirs.eachWithIndex { d, i -> vars.put("updir_" + (i + 1), d) }
files.eachWithIndex { f, i -> vars.put("upfile_" + (i + 1), f) }
vars.put("upload_entry", entry.name)
log.info("upload plan: entry=${entry.name} dirs=${dirs.size()} files=${files.size()}")
