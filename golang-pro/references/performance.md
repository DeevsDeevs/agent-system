# Performance Optimization

## Memory and Allocations

### Proper use of `make()`

Preallocate slices and maps when size is known:

```go
// Bad: Multiple allocations as slice grows
var items []Item
for i := 0; i < 1000; i++ {
    items = append(items, Item{ID: i})
}

// Good: Single allocation
items := make([]Item, 0, 1000)
for i := 0; i < 1000; i++ {
    items = append(items, Item{ID: i})
}

// Best: If you know final size exactly
items := make([]Item, 1000)
for i := 0; i < 1000; i++ {
    items[i] = Item{ID: i}
}
```

For maps:

```go
// Bad: Multiple rehashes as map grows
m := make(map[string]int)
for i := 0; i < 10000; i++ {
    m[fmt.Sprintf("key%d", i)] = i
}

// Good: Preallocate
m := make(map[string]int, 10000)
for i := 0; i < 10000; i++ {
    m[fmt.Sprintf("key%d", i)] = i
}
```

### Using `sync.Pool` for Object Reuse

Speeds up by 10-20%, reduces memory 2-25x for frequently allocated objects:

```go
var bufferPool = sync.Pool{
    New: func() interface{} {
        return new(bytes.Buffer)
    },
}

func processData(data []byte) string {
    buf := bufferPool.Get().(*bytes.Buffer)
    buf.Reset()
    defer bufferPool.Put(buf)

    buf.Write(data)
    buf.WriteString(" processed")
    return buf.String()
}
```

### Avoiding Allocations in Hot Paths

Move allocations outside tight loops:

```go
// Bad: Allocates on every iteration
for i := 0; i < 1000000; i++ {
    result := make([]byte, 1024)
    process(result)
}

// Good: Reuse buffer
result := make([]byte, 1024)
for i := 0; i < 1000000; i++ {
    process(result)
}
```

### Avoiding `defer` in Loops

`defer` is relatively expensive and stacks up in loops:

```go
// Bad: 1000 deferred calls
for i := 0; i < 1000; i++ {
    mu.Lock()
    defer mu.Unlock()  // All defers execute at function end
    process(i)
}

// Good: Explicit unlock
for i := 0; i < 1000; i++ {
    mu.Lock()
    process(i)
    mu.Unlock()
}

// Or use function scope
for i := 0; i < 1000; i++ {
    func() {
        mu.Lock()
        defer mu.Unlock()
        process(i)
    }()
}
```

## String and I/O Operations

### Using Write Buffers

`strings.Builder`, `bytes.Buffer`, `bufio` are significantly faster:

```go
// Bad: Multiple allocations
var s string
for i := 0; i < 1000; i++ {
    s += fmt.Sprintf("item%d,", i)  // New allocation each time
}

// Good: Single allocation with strings.Builder
var builder strings.Builder
builder.Grow(5000)  // Preallocate if size is known
for i := 0; i < 1000; i++ {
    builder.WriteString("item")
    builder.WriteString(strconv.Itoa(i))
    builder.WriteString(",")
}
s := builder.String()
```

Benchmark results: `strings.Builder` is 5x faster than `+=` (2x on memory, 4x on allocations).

### Using `strconv` Instead of `fmt.Sprintf`

20x faster and zero allocations:

```go
// Bad: Allocates and slow
s := fmt.Sprintf("%d", 12345)

// Good: 20x faster, no allocations
s := strconv.Itoa(12345)

// For other types
s := strconv.FormatFloat(3.14159, 'f', 2, 64)
s := strconv.FormatBool(true)
```

### Regular Expressions vs `strings` Package

Use `strings` when possible - 10x faster than `regexp`:

```go
// Bad: regexp for simple check
matched, _ := regexp.MatchString("hello", text)

// Good: strings package
matched := strings.Contains(text, "hello")
```

When regexp is necessary, compile once:

```go
// Bad: Compiles on every call
func validate(s string) bool {
    matched, _ := regexp.MatchString(`^\d{3}-\d{4}$`, s)
    return matched
}

// Good: Compile once
var phoneRegex = regexp.MustCompile(`^\d{3}-\d{4}$`)

func validate(s string) bool {
    return phoneRegex.MatchString(s)
}
```

### Avoiding `[]byte` ↔ `string` Conversions

These create copies and allocate memory:

```go
// Bad: Multiple conversions
func process(data []byte) {
    s := string(data)  // Allocation
    if strings.Contains(s, "error") {
        // ...
    }
}

// Good: Work with bytes directly
func process(data []byte) {
    if bytes.Contains(data, []byte("error")) {
        // ...
    }
}

// Unsafe zero-copy conversion (use with caution)
import "unsafe"

func bytesToString(b []byte) string {
    return *(*string)(unsafe.Pointer(&b))
}
```

## Concurrency Optimization

### Channels vs Mutexes vs Atomics

Performance hierarchy (fastest to slowest):

1. **Atomic operations** - fastest for simple counters
2. **Channels** - better for coordination
3. **Mutexes** - for complex shared state

```go
// Atomic: Fastest for counters
var counter int64
atomic.AddInt64(&counter, 1)

// Channel: Good for coordination
done := make(chan struct{})
go func() {
    work()
    close(done)
}()
<-done

// Mutex: For complex state
type Cache struct {
    mu    sync.Mutex
    items map[string]interface{}
}
```

### Using Buffered Channels

Buffered channels reduce blocking and improve throughput:

```go
// Bad: Unbuffered blocks on every send
ch := make(chan int)

// Good: Buffer reduces blocking
ch := make(chan int, 100)
```

Size buffer based on expected burst size, not total workload.

### Reusing HTTP Connections

Don't create new HTTP clients/transports repeatedly:

```go
// Bad: Creates new connection pool every time
func fetchData(url string) ([]byte, error) {
    client := &http.Client{Timeout: 10 * time.Second}
    resp, err := client.Get(url)
    // ...
}

// Good: Reuse client (connection pooling)
var httpClient = &http.Client{
    Timeout: 10 * time.Second,
    Transport: &http.Transport{
        MaxIdleConns:        100,
        MaxIdleConnsPerHost: 10,
        IdleConnTimeout:     90 * time.Second,
    },
}

func fetchData(url string) ([]byte, error) {
    resp, err := httpClient.Get(url)
    // ...
}
```

## Data Structure Optimization

### Array Iteration

For large arrays, iterate by reference to avoid copying:

```go
type LargeStruct struct {
    data [1000]int
}

var hugeArray [1000]LargeStruct

// Bad: Copies entire array
for _, v := range hugeArray {
    process(v)
}

// Good: Iterate by reference
for _, v := range &hugeArray {
    process(v)
}
```

### Slice Iteration

For slices, the standard iteration is already optimized by the compiler:

```go
// Both are fine - compiler optimizes
for _, v := range slice {
    v.Field++
}

for i := range slice {
    slice[i].Field++
}
```

**Key insight:** If iterating a slice of structs for a single field, consider using a struct of slices instead (better cache locality):

```go
// Slower: Slice of structs
type Person struct {
    Name string
    Age  int
}
people := []Person{...}
for _, p := range people {
    total += p.Age
}

// Faster: Struct of slices (better cache locality)
type People struct {
    Names []string
    Ages  []int
}
people := People{...}
for _, age := range people.Ages {
    total += age
}
```

### Slice Growth Patterns

Slices grow by doubling when `len < 1024`, then by 25%:

```go
// Default growth
s := make([]int, 0)
s = append(s, 1)  // cap=1
s = append(s, 2)  // cap=2
s = append(s, 3)  // cap=4
// ... continues doubling until cap=1024
// Then grows: 1280, 1600, 2048, etc.
```

For known sizes or custom growth, implement your own:

```go
func appendInt(s []int, v int) []int {
    if len(s) == cap(s) {
        // Grow by 4x instead of 2x to reduce allocations
        newCap := cap(s) * 4
        if newCap == 0 {
            newCap = 8
        }
        newSlice := make([]int, len(s), newCap)
        copy(newSlice, s)
        s = newSlice
    }
    return append(s, v)
}
```

### Map Optimization

Small maps (<10 items) can be slower than linear search in slices:

```go
// For small, fixed sets - slice may be faster
type SmallMap struct {
    keys   []string
    values []int
}

func (m *SmallMap) Get(key string) (int, bool) {
    for i, k := range m.keys {
        if k == key {
            return m.values[i], true
        }
    }
    return 0, false
}
```

For integer keys, use the integer directly (no hashing):

```go
// Bad: Hash overhead for int keys
m := make(map[int]string)

// Good: Use slice when keys are dense
data := make([]string, maxID)
data[id] = value
```

### Large Structs by Pointer

Pass large structs by pointer to avoid copying:

```go
type LargeConfig struct {
    data [1024]byte
    // ... many fields
}

// Bad: Copies 1KB+ on every call
func process(cfg LargeConfig) {
    // ...
}

// Good: Only copies 8 bytes (pointer)
func process(cfg *LargeConfig) {
    // ...
}
```

## CPU Optimization

### Free Operations

These operations have negligible cost:

- `len(slice)`, `len(map)`, `len(string)` - O(1), no computation
- `cap(slice)` - O(1), stored in slice header
- Comparison: `==`, `!=`, `<`, `>`, `<=`, `>=`
- Increment/decrement: `i++`, `i--`
- Bitwise operations: `&`, `|`, `^`, `<<`, `>>`

### Generics Have No Runtime Overhead

Go generics use monomorphization (compile-time specialization):

```go
// No runtime penalty
func Map[T, U any](s []T, f func(T) U) []U {
    result := make([]U, len(s))
    for i, v := range s {
        result[i] = f(v)
    }
    return result
}
```

### Slices Are Cheap to Copy

Slice headers are only 24 bytes (pointer + len + cap):

```go
// Cheap: Only copies 24-byte header
func processSlice(s []int) {
    // Working with same underlying array
}
```

### PGO (Profile-Guided Optimization)

Compile with PGO for 2-7% speedup (sometimes up to 15%):

```bash
# 1. Build and run with profiling
go build -o myapp
./myapp -cpuprofile=cpu.pprof

# 2. Rebuild with PGO
go build -pgo=cpu.pprof -o myapp-optimized
```

### CPU Cache Optimization

- First 128 bytes of structs are addressed faster on some CPUs
- L1 cache: ~32KB per core - optimize for this in tight loops
- L3 cache: Shared across all cores
- Cache lines: 64 bytes - group related data together

```go
// Bad: Poor cache locality
type BadLayout struct {
    hotField1  int64  // Accessed often
    coldField1 [100]byte  // Rarely accessed
    hotField2  int64  // Accessed often
    coldField3 int64  // Accessed often
}

// Good: Hot fields together
type GoodLayout struct {
    hotField1  int64  // \
    hotField2  int64  //  > In same cache line
    hotField3  int64  // /
    coldField1 [100]byte
}
```

### Branch Prediction

Branches (if/switch) are expensive due to pipeline stalls. Predictable branches are faster:

```go
// Predictable: Branch predictor learns pattern
for i := 0; i < n; i++ {
    if i%2 == 0 {  // Predictable pattern
        even++
    }
}

// Unpredictable: Random branches slower
for _, val := range randomData {
    if val > threshold {  // Random pattern
        count++
    }
}
```

For highly random branches, consider branchless code:

```go
// Branchy
if x > y {
    max = x
} else {
    max = y
}

// Branchless (compiler may optimize, but can do manually)
max = x ^ ((x ^ y) & -(int(x < y)))
```

## Code Generation vs Reflection

Optimized approaches (code generation, JIT+SIMD) are significantly faster than reflection:

```go
// encoding/json uses reflection - slower
data, _ := json.Marshal(obj)

// bytedance/sonic uses JIT+SIMD - 2-4x faster
import "github.com/bytedance/sonic"
data, _ := sonic.Marshal(obj)
```

Other examples:
- `protobuf` generates code (fast)
- `sqlx` uses reflection (slower than generated code)
- `go generate` for custom code generation

## Garbage Collection

### GOGC Environment Variable

Controls GC trigger threshold (default: 100 = trigger when heap doubles):

```bash
# Default: GC triggers at 2x heap size
GOGC=100 ./myapp

# Less frequent GC, uses more memory
GOGC=200 ./myapp

# More frequent GC, uses less memory
GOGC=50 ./myapp

# Disable GC completely (use with GOMEMLIMIT)
GOGC=off ./myapp
```

Runtime control:

```go
import "runtime/debug"

// Set to 200%
debug.SetGCPercent(200)

// Disable GC
debug.SetGCPercent(-1)
```

### GOMEMLIMIT

Absolute memory limit (Go 1.19+):

```bash
# Limit to 2GB
GOMEMLIMIT=2GiB ./myapp

# Limit to 512MB
GOMEMLIMIT=512MiB ./myapp
```

Runtime control:

```go
import "runtime/debug"

// Set to 2GB
debug.SetMemoryLimit(2 * 1024 * 1024 * 1024)
```

**Warning:** If `GOMEMLIMIT` is too low, GC will consume all CPU time and your program will stall.

### Finding Heap Escapes

See what escapes to the heap:

```bash
go build -gcflags=-m main.go
# Or
go run -gcflags=-m main.go
```

Example output:
```
./main.go:10:6: can inline add
./main.go:15:13: ... argument does not escape
./main.go:16:13: x escapes to heap
```

### Tracing GC Activity

```go
import (
    "os"
    "runtime/trace"
)

func main() {
    f, _ := os.Create("trace.out")
    trace.Start(f)
    defer trace.Stop()

    // Your code here
}
```

View the trace:

```bash
go tool trace trace.out
```

This opens a web interface showing:
- GC activity over time
- Goroutine execution
- Heap growth
- GC pause times

To measure GC impact, select a time range in the GC section to see detailed stats.

## Readability Best Practices

### Avoid `nil` as Parameter

Don't use `nil` for default cases - clarity over brevity:

```go
// Bad: nil is magic value
func NewServer(cfg *Config) *Server {
    if cfg == nil {
        cfg = DefaultConfig()
    }
    // ...
}

// Good: Explicit default
func NewServer() *Server { /* ... */ }
func NewServerWithConfig(cfg *Config) *Server { /* ... */ }
```

### Use Variadic Parameters for Sequences

```go
// Bad: Forces caller to create slice for single item
func Process(items []int) { /* ... */ }
Process([]int{42})  // Awkward

// Good: Variadic - easy for single or multiple items
func Process(items ...int) { /* ... */ }
Process(42)
Process(1, 2, 3, 4)
```

For at least one required argument:

```go
func Process(first int, rest ...int) {
    // Guarantees at least one item
}
```

### Leave Concurrency to the Caller

Return channels, don't create goroutines internally:

```go
// Bad: Forces async execution
func FetchData() {
    go func() {
        // Can't control concurrency or wait for completion
    }()
}

// Good: Return channel, let caller decide
func FetchData() <-chan Result {
    ch := make(chan Result)
    go func() {
        // Caller can control when/how to consume
        defer close(ch)
        // ...
    }()
    return ch
}

// Even better: Synchronous, let caller add concurrency
func FetchData() (Result, error) {
    // Caller can: go fetchData() if they want async
    return result, nil
}
```

## Quick Reference

| Optimization | Impact | When to Use |
|-------------|---------|------------|
| Preallocate slices/maps | 2-10x | Size is known or estimatable |
| `sync.Pool` | 10-25x memory | Frequently allocated objects |
| `strings.Builder` | 5x | String concatenation |
| `strconv` vs `fmt` | 20x | Number to string conversion |
| `strings` vs `regexp` | 10x | Simple string operations |
| Buffered channels | 2-3x | High-throughput pipelines |
| Atomic vs Mutex | 2-5x | Simple counters/flags |
| PGO compilation | 2-15% | Production builds |
| Struct of slices | 2-4x | Iterating for single field |
| Avoid `defer` in loops | 2-3x | Hot loops (1000+ iterations) |

## Profiling Commands

```bash
# CPU profiling
go test -cpuprofile=cpu.prof -bench .
go tool pprof cpu.prof

# Memory profiling
go test -memprofile=mem.prof -bench .
go tool pprof mem.prof

# Escape analysis
go build -gcflags=-m

# Trace analysis
go test -trace=trace.out
go tool trace trace.out

# Benchmark with memory stats
go test -bench . -benchmem

# PGO build
go build -pgo=cpu.pprof
```
