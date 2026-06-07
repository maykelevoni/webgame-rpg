// Progressive enhancement: let desktop players move with the arrow keys.
// The D-pad buttons already work without any JavaScript; this just submits the
// matching hidden form when an arrow key is pressed.
(function () {
  const byClass = (c) => document.querySelector(".dpad form." + c);
  const map = {
    ArrowUp: "n", ArrowDown: "s", ArrowLeft: "w", ArrowRight: "e",
    k: "n", j: "s", h: "w", l: "e", // vim-style, just for fun
  };
  document.addEventListener("keydown", function (e) {
    const dir = map[e.key];
    if (!dir) return;
    const form = byClass(dir);
    if (form) {
      e.preventDefault();
      form.submit();
    }
  });
})();
