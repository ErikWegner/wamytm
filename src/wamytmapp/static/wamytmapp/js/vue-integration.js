jQuery(
  function initVue() {
    const Counter = {
      data() {
        console.log('data');
        return {
          counter: 0
        }
      }
    }

    Vue.createApp(Counter).mount('#counter')

    console.log('vue integration js');
  }
);