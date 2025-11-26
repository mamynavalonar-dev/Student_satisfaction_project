const wrapper = document.querySelector('.wrapper')
const registerLink = document.querySelector('.register-link')
const loginLink = document.querySelector('.login-link')

registerLink.onclick = () => {
    wrapper.classList.add('active')
}

loginLink.onclick = () => {
    wrapper.classList.remove('active')
}

$(document).ready(function() {
  $('.tlt').textillate({
    loop: false, // true si tu veux que ça recommence en boucle
    in: {
      effect: 'fadeInDown', // effet d’entrée (animate.css)
      delayScale: 1.5,
      delay: 50,
      sync: false
    },
    out: {
      effect: 'fadeOutUp', // effet de sortie
      delayScale: 1.0,
      delay: 50,
      sync: false
    }
  });
});