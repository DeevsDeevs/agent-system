# Testing and Benchmarking

## Table-Driven Tests

```go
package math

import "testing"

func Add(a, b int) int {
    return a + b
}

func TestAdd(t *testing.T) {
    tests := []struct {
        name     string
        a, b     int
        expected int
    }{
        {"positive numbers", 2, 3, 5},
        {"negative numbers", -2, -3, -5},
        {"mixed signs", -2, 3, 1},
        {"zeros", 0, 0, 0},
        {"large numbers", 1000000, 2000000, 3000000},
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            result := Add(tt.a, tt.b)
            if result != tt.expected {
                t.Errorf("Add(%d, %d) = %d; want %d", tt.a, tt.b, result, tt.expected)
            }
        })
    }
}
```

## Subtests and Parallel Execution

```go
func TestParallel(t *testing.T) {
    tests := []struct {
        name  string
        input string
        want  string
    }{
        {"lowercase", "hello", "HELLO"},
        {"uppercase", "WORLD", "WORLD"},
        {"mixed", "HeLLo", "HELLO"},
    }

    for _, tt := range tests {
        tt := tt // Capture range variable for parallel tests
        t.Run(tt.name, func(t *testing.T) {
            t.Parallel() // Run subtests in parallel

            result := strings.ToUpper(tt.input)
            if result != tt.want {
                t.Errorf("got %q, want %q", result, tt.want)
            }
        })
    }
}
```

## Test Helpers and Setup/Teardown

```go
func TestWithSetup(t *testing.T) {
    // Setup
    db := setupTestDB(t)
    defer cleanupTestDB(t, db)

    tests := []struct {
        name string
        user User
    }{
        {"valid user", User{Name: "John", Email: "john@example.com"}},
        {"empty name", User{Name: "", Email: "test@example.com"}},
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            err := db.SaveUser(tt.user)
            if err != nil {
                t.Fatalf("SaveUser failed: %v", err)
            }
        })
    }
}

// Helper function (doesn't show in stack trace)
func setupTestDB(t *testing.T) *DB {
    t.Helper()

    db, err := NewDB(":memory:")
    if err != nil {
        t.Fatalf("failed to create test DB: %v", err)
    }
    return db
}

func cleanupTestDB(t *testing.T, db *DB) {
    t.Helper()

    if err := db.Close(); err != nil {
        t.Errorf("failed to close DB: %v", err)
    }
}
```

## Mocking with Interfaces

```go
// Interface to mock
type EmailSender interface {
    Send(to, subject, body string) error
}

// Mock implementation
type MockEmailSender struct {
    SentEmails []Email
    ShouldFail bool
}

type Email struct {
    To, Subject, Body string
}

func (m *MockEmailSender) Send(to, subject, body string) error {
    if m.ShouldFail {
        return fmt.Errorf("failed to send email")
    }
    m.SentEmails = append(m.SentEmails, Email{to, subject, body})
    return nil
}

// Test using mock
func TestUserService_Register(t *testing.T) {
    mockSender := &MockEmailSender{}
    service := NewUserService(mockSender)

    err := service.Register("user@example.com")
    if err != nil {
        t.Fatalf("Register failed: %v", err)
    }

    if len(mockSender.SentEmails) != 1 {
        t.Errorf("expected 1 email sent, got %d", len(mockSender.SentEmails))
    }

    email := mockSender.SentEmails[0]
    if email.To != "user@example.com" {
        t.Errorf("expected email to user@example.com, got %s", email.To)
    }
}
```

## Benchmarking

```go
func BenchmarkAdd(b *testing.B) {
    for i := 0; i < b.N; i++ {
        Add(100, 200)
    }
}

// Benchmark with subtests
func BenchmarkStringOperations(b *testing.B) {
    benchmarks := []struct {
        name  string
        input string
    }{
        {"short", "hello"},
        {"medium", strings.Repeat("hello", 10)},
        {"long", strings.Repeat("hello", 100)},
    }

    for _, bm := range benchmarks {
        b.Run(bm.name, func(b *testing.B) {
            for i := 0; i < b.N; i++ {
                _ = strings.ToUpper(bm.input)
            }
        })
    }
}

// Benchmark with setup
func BenchmarkMapOperations(b *testing.B) {
    m := make(map[string]int)
    for i := 0; i < 1000; i++ {
        m[fmt.Sprintf("key%d", i)] = i
    }

    b.ResetTimer() // Don't count setup time

    for i := 0; i < b.N; i++ {
        _ = m["key500"]
    }
}

// Parallel benchmark
func BenchmarkConcurrentAccess(b *testing.B) {
    var counter int64

    b.RunParallel(func(pb *testing.PB) {
        for pb.Next() {
            atomic.AddInt64(&counter, 1)
        }
    })
}

// Memory allocation benchmark
func BenchmarkAllocation(b *testing.B) {
    b.ReportAllocs() // Report allocations

    for i := 0; i < b.N; i++ {
        s := make([]int, 1000)
        _ = s
    }
}
```

## Fuzzing (Go 1.18+)

```go
func FuzzReverse(f *testing.F) {
    // Seed corpus
    testcases := []string{"hello", "world", "123", ""}
    for _, tc := range testcases {
        f.Add(tc)
    }

    f.Fuzz(func(t *testing.T, input string) {
        reversed := Reverse(input)
        doubleReversed := Reverse(reversed)

        if input != doubleReversed {
            t.Errorf("Reverse(Reverse(%q)) = %q, want %q", input, doubleReversed, input)
        }
    })
}

// Fuzz with multiple parameters
func FuzzAdd(f *testing.F) {
    f.Add(1, 2)
    f.Add(0, 0)
    f.Add(-1, 1)

    f.Fuzz(func(t *testing.T, a, b int) {
        result := Add(a, b)

        // Properties that should always hold
        if result < a && b >= 0 {
            t.Errorf("Add(%d, %d) = %d; result should be >= a when b >= 0", a, b, result)
        }
    })
}
```

## Test Coverage

### Basic Coverage Commands

```bash
# Simple coverage percentage
go test -cover

# Output: coverage: 85.5% of statements

# Coverage by package
go test ./... -cover

# Generate coverage profile
go test -coverprofile=coverage.out

# View coverage in terminal
go tool cover -func=coverage.out

# Generate HTML coverage report (recommended)
go test -coverprofile=coverage.out
go tool cover -html=coverage.out

# Open HTML report in browser automatically
go tool cover -html=coverage.out -o coverage.html
xdg-open coverage.html  # Linux
open coverage.html      # macOS
start coverage.html     # Windows
```

### Coverage Modes

```bash
# Set coverage mode (default: set)
go test -covermode=set -coverprofile=coverage.out

# Count mode: How many times each statement executed
go test -covermode=count -coverprofile=coverage.out

# Atomic mode: Like count, but thread-safe (use with -race)
go test -covermode=atomic -race -coverprofile=coverage.out
```

**Coverage modes:**
- `set`: Boolean - was statement executed? (fastest)
- `count`: Integer - how many times was statement executed?
- `atomic`: Thread-safe count (required with `-race`)

### Viewing HTML Coverage Report

The HTML report shows your code with color coding:

- **Green**: Covered code (executed by tests)
- **Red**: Uncovered code (not executed by tests)
- **Gray**: Not tracked (comments, package declarations)

```bash
# Generate and view HTML report
go test -coverprofile=coverage.out
go tool cover -html=coverage.out
```

The HTML interface allows you to:
1. See overall coverage percentage
2. Browse files and see coverage line-by-line
3. Identify untested code paths
4. Click through file dropdown to examine different packages

### Coverage for Specific Packages

```bash
# Single package
go test -cover ./pkg/server

# Multiple packages
go test -cover ./pkg/server ./pkg/client

# All packages recursively
go test -cover ./...

# Exclude vendor and test files
go test -cover $(go list ./... | grep -v /vendor/)
```

### Per-Function Coverage

```bash
# Generate profile
go test -coverprofile=coverage.out

# View per-function coverage
go tool cover -func=coverage.out

# Output example:
# myproject/server.go:15:    StartServer     100.0%
# myproject/server.go:42:    HandleRequest    87.5%
# myproject/client.go:10:    Connect          66.7%
# total:                     (statements)     85.5%
```

### Coverage with Benchmarks

```bash
# Include benchmark coverage
go test -bench . -coverprofile=coverage.out

# Combine regular tests and benchmarks
go test -v -bench . -coverprofile=coverage.out
go tool cover -html=coverage.out
```

### Multi-Package Coverage

```bash
# Generate coverage for all packages
go test -coverprofile=coverage.out ./...

# Better: Use coverpkg to include all packages
go test -coverpkg=./... -coverprofile=coverage.out ./...

# View combined coverage
go tool cover -html=coverage.out
```

### Setting Coverage Thresholds

```bash
# Script to enforce minimum coverage
#!/bin/bash
COVERAGE=$(go test -cover ./... | grep -o '[0-9]\+\.[0-9]\+%' | head -1 | sed 's/%//')
THRESHOLD=80.0

if (( $(echo "$COVERAGE < $THRESHOLD" | bc -l) )); then
    echo "Coverage $COVERAGE% is below threshold $THRESHOLD%"
    exit 1
else
    echo "Coverage $COVERAGE% meets threshold $THRESHOLD%"
fi
```

### Ignoring Generated Files

```bash
# Exclude generated files from coverage
go test -coverprofile=coverage.out ./...
cat coverage.out | grep -v "_generated.go" > coverage.filtered.out
go tool cover -html=coverage.filtered.out
```

### Coverage in CI/CD

```yaml
# GitHub Actions example
- name: Run tests with coverage
  run: |
    go test -v -race -covermode=atomic -coverprofile=coverage.out ./...
    go tool cover -func=coverage.out

- name: Upload coverage to Codecov
  uses: codecov/codecov-action@v3
  with:
    file: ./coverage.out
    fail_ci_if_error: true
```

### Example Test with Coverage Focus

```go
func TestCalculate(t *testing.T) {
    tests := []struct {
        name     string
        input    int
        expected int
    }{
        {"zero", 0, 0},
        {"positive", 5, 25},
        {"negative", -3, 9},
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            result := Calculate(tt.input)
            if result != tt.expected {
                t.Errorf("Calculate(%d) = %d; want %d", tt.input, result, tt.expected)
            }
        })
    }
}

// Calculate function with multiple branches
func Calculate(n int) int {
    if n == 0 {         // Test coverage: covered by "zero" test
        return 0
    }
    if n < 0 {          // Test coverage: covered by "negative" test
        return n * n
    }
    return n * n        // Test coverage: covered by "positive" test
}
```

### Analyzing Uncovered Code

When viewing the HTML report, focus on:

1. **Error handling paths**: Often missed in tests
```go
result, err := riskyOperation()
if err != nil {
    return fmt.Errorf("failed: %w", err)  // Is this tested?
}
```

2. **Edge cases**: Boundary conditions
```go
if len(items) == 0 {
    return nil  // Is this tested?
}
```

3. **Else branches**: Negative cases
```go
if isValid {
    process()
} else {
    reject()  // Is this tested?
}
```

### Coverage Best Practices

- **80%+ coverage** is a good target for most projects
- **100% coverage** is not always necessary or practical
- Focus on **critical paths** and **business logic**
- Don't test **generated code** or **trivial getters/setters**
- Use coverage to **find gaps**, not as a quality metric alone
- Combine with **code review** and **integration testing**

### Quick Reference

| Command | Description |
|---------|-------------|
| `go test -cover` | Show coverage percentage |
| `go test -coverprofile=coverage.out` | Generate coverage profile |
| `go tool cover -html=coverage.out` | View HTML report |
| `go tool cover -func=coverage.out` | Per-function coverage |
| `go test -covermode=count` | Count execution times |
| `go test -covermode=atomic -race` | Thread-safe coverage with race detector |
| `go test -coverpkg=./...` | Include all packages in coverage |

## Race Detector

```go
// Run with: go test -race

func TestConcurrentAccess(t *testing.T) {
    var counter int
    var wg sync.WaitGroup

    // This will fail with -race if not synchronized
    for i := 0; i < 10; i++ {
        wg.Add(1)
        go func() {
            defer wg.Done()
            counter++ // Data race!
        }()
    }

    wg.Wait()
}

// Fixed version with mutex
func TestConcurrentAccessSafe(t *testing.T) {
    var counter int
    var mu sync.Mutex
    var wg sync.WaitGroup

    for i := 0; i < 10; i++ {
        wg.Add(1)
        go func() {
            defer wg.Done()
            mu.Lock()
            counter++
            mu.Unlock()
        }()
    }

    wg.Wait()

    if counter != 10 {
        t.Errorf("expected 10, got %d", counter)
    }
}
```

## Golden Files

```go
import (
    "os"
    "path/filepath"
    "testing"
)

func TestRenderHTML(t *testing.T) {
    data := Data{Title: "Test", Content: "Hello"}
    result := RenderHTML(data)

    goldenFile := filepath.Join("testdata", "expected.html")

    if *update {
        // Update golden file: go test -update
        os.WriteFile(goldenFile, []byte(result), 0644)
    }

    expected, err := os.ReadFile(goldenFile)
    if err != nil {
        t.Fatalf("failed to read golden file: %v", err)
    }

    if result != string(expected) {
        t.Errorf("output doesn't match golden file\ngot:\n%s\nwant:\n%s", result, expected)
    }
}

var update = flag.Bool("update", false, "update golden files")
```

## Integration Tests

```go
// integration_test.go
// +build integration

package myapp

import (
    "testing"
    "time"
)

func TestIntegration(t *testing.T) {
    if testing.Short() {
        t.Skip("skipping integration test in short mode")
    }

    // Long-running integration test
    server := startTestServer(t)
    defer server.Stop()

    time.Sleep(100 * time.Millisecond) // Wait for server

    client := NewClient(server.URL)
    resp, err := client.Get("/health")
    if err != nil {
        t.Fatalf("health check failed: %v", err)
    }

    if resp.Status != "ok" {
        t.Errorf("expected status ok, got %s", resp.Status)
    }
}

// Run: go test -tags=integration
// Run short tests only: go test -short
```

## Testable Examples

```go
// Example tests that appear in godoc
func ExampleAdd() {
    result := Add(2, 3)
    fmt.Println(result)
    // Output: 5
}

func ExampleAdd_negative() {
    result := Add(-2, -3)
    fmt.Println(result)
    // Output: -5
}

// Unordered output
func ExampleKeys() {
    m := map[string]int{"a": 1, "b": 2, "c": 3}
    keys := Keys(m)
    for _, k := range keys {
        fmt.Println(k)
    }
    // Unordered output:
    // a
    // b
    // c
}
```

## Quick Reference

| Command | Description |
|---------|-------------|
| `go test` | Run tests |
| `go test -v` | Verbose output |
| `go test -run TestName` | Run specific test |
| `go test -bench .` | Run benchmarks |
| `go test -cover` | Show coverage |
| `go test -race` | Run race detector |
| `go test -short` | Skip long tests |
| `go test -fuzz FuzzName` | Run fuzzing |
| `go test -cpuprofile cpu.prof` | CPU profiling |
| `go test -memprofile mem.prof` | Memory profiling |
