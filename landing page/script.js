document.querySelectorAll('.aba').forEach(function (aba) {
  aba.addEventListener('click', function () {
    document.querySelectorAll('.aba').forEach(function (a) { a.classList.remove('ativa'); });
    document.querySelectorAll('.moldura-tela').forEach(function (m) { m.classList.remove('ativa'); });
    aba.classList.add('ativa');
    document.getElementById(aba.dataset.aba).classList.add('ativa');
  });
});

const observador = new IntersectionObserver(function (entradas) {
  entradas.forEach(function (entrada) {
    if (entrada.isIntersecting) {
      entrada.target.style.opacity = 1;
      entrada.target.style.transform = 'translateY(0)';
    }
  });
}, { threshold: 0.12 });

document.querySelectorAll('section').forEach(function (secao) {
  secao.style.opacity = 0;
  secao.style.transform = 'translateY(16px)';
  secao.style.transition = 'opacity .5s ease, transform .5s ease';
  observador.observe(secao);
});
