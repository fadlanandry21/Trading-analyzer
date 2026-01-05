<template>
  <div id="app">
    <!-- Animated Background Curves -->
    <div class="curved-bg">
      <svg width="100%" height="100%" preserveAspectRatio="none">
        <path class="curve curve-1" d="M0,300 Q200,100 400,200 T800,150 T1200,250 T1600,200 T2000,300 L2000,800 L0,800 Z"/>
        <path class="curve curve-2" d="M0,400 Q300,300 600,450 T1200,350 T1800,500 T2400,400 L2400,800 L0,800 Z"/>
        <path class="curve curve-3" d="M0,200 Q400,350 800,150 T1600,300 T2400,200 L2400,800 L0,800 Z"/>
        <path class="curve curve-4" d="M0,500 Q250,450 500,550 T1000,400 T1500,600 T2000,450 L2000,800 L0,800 Z"/>
        <path class="curve curve-5" d="M0,350 Q350,250 700,400 T1400,300 T2100,450 L2100,800 L0,800 Z"/>
      </svg>
      
      <!-- Glowing Orbs -->
      <div class="orb" style="width: 400px; height: 400px; background: rgba(34,211,238,0.2); top: 10%; left: 10%;"></div>
      <div class="orb" style="width: 300px; height: 300px; background: rgba(168,85,247,0.2); top: 50%; right: 10%; animation-delay: 1s;"></div>
      <div class="orb" style="width: 350px; height: 350px; background: rgba(236,72,153,0.15); bottom: 20%; left: 30%; animation-delay: 2s;"></div>
      
      <!-- Floating Particles -->
      <div v-for="n in 20" :key="'p'+n" class="particle" 
           :style="{ left: Math.random() * 100 + '%', animationDelay: Math.random() * 15 + 's', animationDuration: (10 + Math.random() * 10) + 's' }">
      </div>
    </div>

    <!-- Crypto Ticker -->
    <div class="ticker-wrap">
      <div class="ticker">
        <div v-for="(coin, index) in cryptoTicker" :key="index" class="crypto-item">
          <span class="font-semibold">{{ coin.symbol }}</span>
          <span>${{ coin.price.toLocaleString() }}</span>
          <span :class="coin.change >= 0 ? 'green' : 'red'">
            {{ coin.change >= 0 ? '+' : '' }}{{ coin.change }}%
          </span>
        </div>
        <div v-for="(coin, index) in cryptoTicker" :key="'dup'+index" class="crypto-item">
          <span class="font-semibold">{{ coin.symbol }}</span>
          <span>${{ coin.price.toLocaleString() }}</span>
          <span :class="coin.change >= 0 ? 'green' : 'red'">
            {{ coin.change >= 0 ? '+' : '' }}{{ coin.change }}%
          </span>
        </div>
      </div>
    </div>

    <!-- Navigation -->
    <nav class="main-content flex items-center justify-between px-8 py-6 max-w-7xl mx-auto">
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 rounded-xl from-cyan-400 to-purple-500 flex items-center justify-center">
          <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
          </svg>
        </div>
        <span class="text-2xl font-bold text-white">Hybrid<span class="gradient-text">Analyzer</span></span>
      </div>
      <div class="hidden md:flex items-center gap-8">
        <a href="#" class="nav-link">Analisis</a>
        <a href="#" class="nav-link">Market</a>
        <a href="#" class="nav-link">Signals</a>
        <a href="#" class="nav-link">Pricing</a>
      </div>
      <div class="flex items-center gap-4">
        <button class="text-white/70 hover:text-white transition">Masuk</button>
        <button class="btn-primary">Daftar Gratis</button>
      </div>
    </nav>

    <!-- Main Hero Section -->
    <main class="main-content min-h-screen flex flex-col justify-center items-center text-center px-4">
      <div class="max-w-5xl mx-auto">
        <!-- Badge -->
        <div class="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/5 border border-white/10 mb-8">
          <span class="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
          <span class="text-sm text-white/70">Analisis Real-time</span>
        </div>

        <!-- Main Heading -->
        <h1 class="text-5xl md:text-7xl font-bold mb-6 leading-tight">
          <span class="text-white">Analisis Kripto</span><br>
          <span class="gradient-text glow">Masa Depan Finansial</span>
        </h1>

        <!-- Subtitle -->
        <p class="text-xl text-white/60 max-w-2xl mx-auto mb-12 leading-relaxed">
          Platform analisis cryptocurrency terlengkap dengan teknologi AI. 
          Dapatkan insight mendalam, prediksi akurat, dan signals trading 
          dari para ahli.
        </p>

        <!-- Buttons -->
        <div class="flex flex-col sm:flex-row items-center justify-center gap-4 mb-16">
          <button class="btn-primary flex items-center gap-2 group">
            <svg class="w-5 h-5 group-hover:animate-bounce" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
            </svg>
            Mulai Analisis
          </button>
        </div>

        <!-- Stats Cards -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-4xl mx-auto">
          <div v-for="(stat, index) in stats" :key="index" class="stat-card group cursor-pointer">
            <div class="flex items-center gap-3 mb-3">
              <div class="w-10 h-10 rounded-lg flex items-center justify-center" :class="stat.bgClass">
                <span class="text-xl">{{ stat.icon }}</span>
              </div>
            </div>
            <h3 class="text-2xl font-bold text-white mb-1">{{ stat.value }}</h3>
            <p class="text-white/50 text-sm">{{ stat.label }}</p>
            <div class="mt-3 h-1 bg-white/10 rounded-full overflow-hidden">
              <div class="h-full rounded-full transition-all duration-500" :class="stat.barClass" :style="{ width: stat.barWidth + '%' }"></div>
            </div>
          </div>
        </div>
      </div>

      <!-- Scroll Indicator -->
      <div class="absolute bottom-10 left-1/2 transform -translate-x-1/2">
        <div class="scroll-indicator text-white/30">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 14l-7 7m0 0l-7-7m7 7V3"/>
          </svg>
        </div>
      </div>
    </main>
  </div>
</template>

<script>
export default {
  name: 'App',
  data() {
    return {
      cryptoTicker: [
        { symbol: 'BTC', price: 43250.80, change: 2.34 },
        { symbol: 'ETH', price: 2280.50, change: 4.12 },
        { symbol: 'BNB', price: 312.40, change: -1.23 },
        { symbol: 'SOL', price: 98.75, change: 8.45 },
        { symbol: 'XRP', price: 0.62, change: 1.87 },
        { symbol: 'ADA', price: 0.52, change: -2.34 },
        { symbol: 'DOGE', price: 0.082, change: 5.67 },
        { symbol: 'DOT', price: 7.23, change: 3.21 },
      ],
      stats: [
        {
          icon: '📊',
          value: '500K+',
          label: 'Analisis Harian',
          barWidth: 85,
          barClass: 'bg-gradient-to-r from-cyan-400 to-purple-500',
          bgClass: 'bg-cyan-500/10'
        },
        {
          icon: '🎯',
          value: '94.7%',
          label: 'Akurasi Sinyal',
          barWidth: 95,
          barClass: 'bg-gradient-to-r from-purple-500 to-pink-500',
          bgClass: 'bg-purple-500/10'
        },
        {
          icon: '👥',
          value: '120K+',
          label: 'Trader Aktif',
          barWidth: 70,
          barClass: 'bg-gradient-to-r from-green-400 to-cyan-400',
          bgClass: 'bg-green-500/10'
        }
      ]
    };
  }
};
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

* {
  font-family: 'Inter', sans-serif;
}

.font-mono {
  font-family: 'JetBrains Mono', monospace;
}

#app {
  background: #000;
  overflow-x: hidden;
}

/* Animated curved lines background */
.curved-bg {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 0;
  overflow: hidden;
}

.curve {
  position: absolute;
  opacity: 0.15;
  fill: none;
  stroke-width: 2;
}

.curve-1 { stroke: #22d3ee; animation: moveCurve1 8s ease-in-out infinite; }
.curve-2 { stroke: #a855f7; animation: moveCurve2 10s ease-in-out infinite; }
.curve-3 { stroke: #10b981; animation: moveCurve3 12s ease-in-out infinite; }
.curve-4 { stroke: #f59e0b; animation: moveCurve4 9s ease-in-out infinite; }
.curve-5 { stroke: #ec4899; animation: moveCurve5 11s ease-in-out infinite; }

@keyframes moveCurve1 {
  0%, 100% { transform: translateX(0) translateY(0) scaleY(1); }
  50% { transform: translateX(-50px) translateY(-20px) scaleY(1.1); }
}

@keyframes moveCurve2 {
  0%, 100% { transform: translateX(0) translateY(0) scaleY(1); }
  50% { transform: translateX(50px) translateY(30px) scaleY(1.05); }
}

@keyframes moveCurve3 {
  0%, 100% { transform: translateX(0) scale(1); }
  50% { transform: translateX(-30px) scale(1.08); }
}

@keyframes moveCurve4 {
  0%, 100% { transform: translateY(0) rotate(0deg); }
  50% { transform: translateY(-40px) rotate(2deg); }
}

@keyframes moveCurve5 {
  0%, 100% { transform: translateX(0) translateY(0); }
  50% { transform: translateX(40px) translateY(-25px); }
}

/* Floating particles */
.particle {
  position: absolute;
  width: 4px;
  height: 4px;
  background: radial-gradient(circle, rgba(34,211,238,0.8) 0%, transparent 70%);
  border-radius: 50%;
  animation: float 15s infinite;
}

@keyframes float {
  0%, 100% {
    transform: translateY(100vh) rotate(0deg);
    opacity: 0;
  }
  10% { opacity: 1; }
  90% { opacity: 1; }
  100% {
    transform: translateY(-100vh) rotate(720deg);
    opacity: 0;
  }
}

/* Glowing orbs */
.orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  animation: pulse 4s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 0.3; transform: scale(1); }
  50% { opacity: 0.6; transform: scale(1.2); }
}

/* Main content */
.main-content {
  position: relative;
  z-index: 10;
}

/* Gradient text */
.gradient-text {
  background: linear-gradient(135deg, #22d3ee 0%, #a855f7 50%, #ec4899 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

/* Modern button styles */
.btn-primary {
  position: relative;
  padding: 16px 40px;
  font-size: 16px;
  font-weight: 600;
  color: #fff;
  background: linear-gradient(135deg, rgba(34,211,238,0.1) 0%, rgba(168,85,247,0.1) 100%);
  border: 1px solid rgba(168,85,247,0.3);
  border-radius: 12px;
  cursor: pointer;
  overflow: hidden;
  transition: all 0.3s ease;
}

.btn-primary::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(34,211,238,0.3), transparent);
  transition: left 0.5s ease;
}

.btn-primary:hover::before {
  left: 100%;
}

.btn-primary:hover {
  border-color: #22d3ee;
  box-shadow: 0 0 30px rgba(34,211,238,0.3), 0 0 60px rgba(168,85,247,0.2);
  transform: translateY(-3px);
}

.btn-secondary {
  padding: 16px 40px;
  font-size: 16px;
  font-weight: 600;
  color: #fff;
  background: transparent;
  border: 1px solid rgba(255,255,255,0.2);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.btn-secondary::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  width: 0;
  height: 2px;
  background: linear-gradient(90deg, #22d3ee, #a855f7);
  transition: width 0.3s ease;
}

.btn-secondary:hover {
  border-color: rgba(255,255,255,0.5);
  background: rgba(255,255,255,0.05);
}

.btn-secondary:hover::after {
  width: 100%;
}

/* Stat cards */
.stat-card {
  background: rgba(255,255,255,0.03);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 16px;
  padding: 24px;
  transition: all 0.3s ease;
}

.stat-card:hover {
  background: rgba(255,255,255,0.06);
  border-color: rgba(168,85,247,0.3);
  transform: translateY(-5px);
  box-shadow: 0 20px 40px rgba(0,0,0,0.3);
}

/* Navbar */
.nav-link {
  position: relative;
  color: rgba(255,255,255,0.7);
  transition: color 0.3s ease;
}

.nav-link:hover {
  color: #fff;
}

.nav-link::after {
  content: '';
  position: absolute;
  bottom: -4px;
  left: 0;
  width: 0;
  height: 2px;
  background: linear-gradient(90deg, #22d3ee, #a855f7);
  transition: width 0.3s ease;
}

.nav-link:hover::after {
  width: 100%;
}

/* Crypto ticker animation */
.ticker-wrap {
  overflow: hidden;
  background: rgba(0,0,0,0.5);
  padding: 12px 0;
  border-top: 1px solid rgba(255,255,255,0.1);
  border-bottom: 1px solid rgba(255,255,255,0.1);
}

.ticker {
  display: flex;
  animation: ticker 30s linear infinite;
}

@keyframes ticker {
  0% { transform: translateX(0); }
  100% { transform: translateX(-50%); }
}

.crypto-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 32px;
  white-space: nowrap;
}

.crypto-item .green { color: #10b981; }
.crypto-item .red { color: #ef4444; }

/* Glow effect */
.glow {
  animation: glow 2s ease-in-out infinite alternate;
}

@keyframes glow {
  from { filter: drop-shadow(0 0 10px rgba(34,211,238,0.5)); }
  to { filter: drop-shadow(0 0 20px rgba(168,85,247,0.8)); }
}

/* Scroll indicator */
.scroll-indicator {
  animation: bounce 2s infinite;
}

@keyframes bounce {
  0%, 20%, 50%, 80%, 100% { transform: translateY(0); }
  40% { transform: translateY(-10px); }
  60% { transform: translateY(-5px); }
}
</style>