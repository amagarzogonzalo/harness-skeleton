---
name: rust-unsafe
description: Rust unsafe-code review and soundness checklist. Trigger when adding unsafe, FFI, transmute, MaybeUninit, unsafe impl, or investigating UB.
---

# Rust unsafe

## Before writing unsafe

- Can safe Rust do it? Check `std`, `bytemuck`, `zerocopy`, `smallvec`, and the
  `nom`/`bytes` family before writing a raw-pointer loop.
- If not, write the **safety contract** first: the invariant, who upholds it,
  and what violates it. Then write the code to that contract.

## Every unsafe block needs

```rust
// SAFETY: `ptr` comes from `Vec::as_ptr` and the vector is not mutated for the
// lifetime of `slice`; len is the initialized length.
let slice = unsafe { std::slice::from_raw_parts(ptr, len) };
```

- A comment that says "safe because we checked" without saying **what** was
  checked is not a safety comment.
- Keep the unsafe block as small as possible. Safe code around it.
- Prefer a safe abstraction with a private unsafe core over unsafe at every call
  site.

## Checklist

- [ ] Pointer is non-null, aligned, and points to initialized memory.
- [ ] The allocation outlives every reference derived from it.
- [ ] No `&mut` aliases any other reference for its lifetime.
- [ ] `len` is in bounds and in elements, not bytes, where required.
- [ ] `transmute` preserves size, alignment, and validity; prefer `From`.
- [ ] `MaybeUninit` is written before `assume_init`; drop is handled.
- [ ] FFI types are `#[repr(C)]`; ownership and nullability are documented.
- [ ] `unsafe impl Send/Sync` has a written argument that holds for all fields.
- [ ] Panics cannot unwind across an `extern "C"` boundary.
- [ ] `#[deny(unsafe_op_in_unsafe_fn)]` is on; unsafe operations are explicit.

## Evidence

```bash
cargo +nightly miri test
cargo clippy --all-targets --all-features -- -D warnings
cargo geiger                       # optional: unsafe density
rg -n "unsafe|transmute|MaybeUninit|from_raw_parts|unsafe impl" .
```

Miri is necessary, not sufficient. A clean run does not prove soundness.

## Stop conditions

- You cannot state the invariant: do not write the unsafe block.
- The unsafe block needs a new dependency to justify it: ask first.
- The only test is "it did not crash": that is not a soundness test.
