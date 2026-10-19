
const abasTela = Array.from(document.querySelectorAll('.aba'));
const moldurasTela = Array.from(document.querySelectorAll('.moldura-tela'));

let telaAtual = Math.max(
  0,
  moldurasTela.findIndex(function (moldura) {
    return moldura.classList.contains('ativa');
  })
);

function mostrarTela(indice) {
  if (moldurasTela.length === 0) return;

  telaAtual = (indice + moldurasTela.length) % moldurasTela.length;

  abasTela.forEach(function (aba, i) {
    aba.classList.toggle('ativa', i === telaAtual);
  });

  moldurasTela.forEach(function (moldura, i) {
    moldura.classList.toggle('ativa', i === telaAtual);
  });
}

// Navegação pelas abas
abasTela.forEach(function (aba, indice) {
  aba.addEventListener('click', function () {
    mostrarTela(indice);
  });
});

// Seta para a imagem anterior
const setaAnterior = document.querySelector('.seta-tela.anterior');

if (setaAnterior) {
  setaAnterior.addEventListener('click', function () {
    mostrarTela(telaAtual - 1);
  });
}

// Seta para a próxima imagem
const setaProxima = document.querySelector('.seta-tela.proxima');

if (setaProxima) {
  setaProxima.addEventListener('click', function () {
    mostrarTela(telaAtual + 1);
  });
}

// Animação das seções ao aparecerem na tela
const observador = new IntersectionObserver(
  function (entradas) {
    entradas.forEach(function (entrada) {
      if (entrada.isIntersecting) {
        entrada.target.style.opacity = 1;
        entrada.target.style.transform = 'translateY(0)';
        observador.unobserve(entrada.target);
      }
    });
  },
  { threshold: 0.12 }
);

document.querySelectorAll('section').forEach(function (secao) {
  secao.style.opacity = 0;
  secao.style.transform = 'translateY(16px)';
  secao.style.transition = 'opacity .5s ease, transform .5s ease';

  observador.observe(secao);
});
