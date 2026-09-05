const tabs = [...document.querySelectorAll(".tab")];
const allSlides = [...document.querySelectorAll(".slide")];
const prev = document.querySelector("#prev");
const next = document.querySelector("#next");
const counter = document.querySelector("#counter");

let activeDeck = "intern";
let index = 0;

function deckSlides() {
  return allSlides.filter((slide) => slide.dataset.deck === activeDeck);
}

function render() {
  const slides = deckSlides();
  allSlides.forEach((slide) => slide.classList.remove("active"));
  slides[index].classList.add("active");
  counter.textContent = `${index + 1} / ${slides.length}`;
  tabs.forEach((tab) => tab.classList.toggle("active", tab.dataset.target === activeDeck));
}

function go(delta) {
  const slides = deckSlides();
  index = (index + delta + slides.length) % slides.length;
  render();
}

tabs.forEach((tab) => {
  tab.addEventListener("click", () => {
    activeDeck = tab.dataset.target;
    index = 0;
    render();
  });
});

prev.addEventListener("click", () => go(-1));
next.addEventListener("click", () => go(1));

document.addEventListener("keydown", (event) => {
  if (event.key === "ArrowLeft") go(-1);
  if (event.key === "ArrowRight") go(1);
});

render();
