// Pure keyframe interpolation helpers — no three.js imports so Node can test them.
const DT_EPS = 1e-6;

export function bracketForTime(times, tMyr) {
    const n = times.length;
    if (n === 0) return { i: -1, j: -1, alpha: 0 };
    if (tMyr <= times[0]) return { i: 0, j: 0, alpha: 0 };
    if (tMyr >= times[n - 1]) return { i: n - 1, j: n - 1, alpha: 0 };
    let lo = 0;
    let hi = n - 1;
    while (hi - lo > 1) {
        const mid = (lo + hi) >> 1;
        if (times[mid] <= tMyr) lo = mid;
        else hi = mid;
    }
    const dt = times[hi] - times[lo];
    if (dt < DT_EPS) return { i: lo, j: hi, alpha: 1 };
    return { i: lo, j: hi, alpha: (tMyr - times[lo]) / dt };
}

export function lerp3(a, b, alpha) {
    return [
        a[0] + (b[0] - a[0]) * alpha,
        a[1] + (b[1] - a[1]) * alpha,
        a[2] + (b[2] - a[2]) * alpha,
    ];
}
