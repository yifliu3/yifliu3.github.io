(function () {
  var videos = document.querySelectorAll('.project-media video');
  var reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  var connection = navigator.connection;
  var visible = new Set();

  function shouldAnimate() {
    return !reducedMotion.matches && !(connection && connection.saveData);
  }

  function loadVideo(video) {
    var sources = video.querySelectorAll('source[data-src]');
    if (!sources.length) return;
    sources.forEach(function (source) {
      source.src = source.dataset.src;
      source.removeAttribute('data-src');
    });
    video.preload = 'auto';
    video.load();
  }

  function syncPlayback() {
    videos.forEach(function (video) {
      if (visible.has(video) && !document.hidden && shouldAnimate()) {
        loadVideo(video);
        video.play().catch(function () {
          // Keep the poster visible if the browser prevents autoplay.
        });
      } else {
        video.pause();
      }
    });
  }

  // Posters remain available with JavaScript disabled or no observer support.
  if (!('IntersectionObserver' in window)) return;
  videos.forEach(function (video) { video.autoplay = false; });

  var preloadObserver = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting && shouldAnimate()) {
        loadVideo(entry.target);
        preloadObserver.unobserve(entry.target);
      }
    });
  }, { rootMargin: '200px 0px' });

  var playbackObserver = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) visible.add(entry.target);
      else visible.delete(entry.target);
    });
    syncPlayback();
  });

  videos.forEach(function (video) {
    preloadObserver.observe(video);
    playbackObserver.observe(video);
  });
  document.addEventListener('visibilitychange', syncPlayback);
  reducedMotion.addEventListener('change', syncPlayback);
  if (connection) connection.addEventListener('change', syncPlayback);
})();
