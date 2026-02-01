<template>
  <div class="common-layout">
    <el-container class="main-container">
      <el-header class="header">
        <div class="header-content">
          <div>
            <h1>⚡ BLDC AI Simulator</h1>
            <p>Advanced Motor Performance Prediction</p>
          </div>
          <div class="header-actions">
            <!-- New Export Button -->
            <el-button type="success" @click="exportReport" :icon="Document">
              📄 Export Report (PDF)
            </el-button>
          </div>
        </div>
      </el-header>
      
      <el-container>
        <!-- Left Panel: Controls -->
        <el-aside width="400px" class="control-panel">
          <el-card class="box-card">
            <template #header>
              <div class="card-header">
                <span>Design Parameters</span>
              </div>
            </template>
            
            <el-form :model="form" label-position="top">
              
              <el-form-item label="Stator Outer Diameter (OD)">
                <el-slider v-model="form.stator_od" :min="40" :max="150" show-input />
                <div class="unit">mm</div>
              </el-form-item>

              <el-form-item label="Stack Length">
                <el-slider v-model="form.stack_length" :min="10" :max="100" show-input />
                <div class="unit">mm</div>
              </el-form-item>

              <el-form-item label="Airgap Length">
                <el-input-number v-model="form.airgap" :precision="2" :step="0.1" :min="0.3" :max="2.0" />
                <span class="unit-text">mm</span>
              </el-form-item>

              <el-form-item label="Turns per Coil">
                <el-input-number v-model="form.turns_per_coil" :min="10" :max="200" />
                <span class="unit-text">turns</span>
              </el-form-item>

              <el-form-item label="Magnet Strength">
                <el-select v-model="form.magnet_rem" placeholder="Select Magnet Grade">
                  <el-option label="N35 (1.18T)" :value="1.18" />
                  <el-option label="N42 (1.28T)" :value="1.28" />
                  <el-option label="N50 (1.40T)" :value="1.40" />
                </el-select>
              </el-form-item>
              
              <el-form-item label="Slot/Pole Config">
                 <el-select v-model="form.slot_pole_combo">
                  <el-option label="12N14P (High Torque)" value="12N14P" />
                  <el-option label="9N6P (High Speed)" value="9N6P" />
                  <el-option label="24N20P (Large Drone)" value="24N20P" />
                </el-select>
              </el-form-item>

              <div class="actions">
                <el-button type="primary" size="large" class="simulate-btn" @click="simulate" :loading="loading">
                  ⚡ Simulate
                </el-button>
              </div>

            </el-form>
          </el-card>
        </el-aside>

        <!-- Right Panel: Visualization & Results -->
        <el-main class="result-panel">
          
          <!-- Top: Metrics -->
          <el-row :gutter="20" class="metrics-row">
            <el-col :span="8">
              <el-card shadow="hover" class="metric-card">
                <div class="metric-title">Kv Rating</div>
                <div class="metric-value">{{ results.kv }} <span class="unit">RPM/V</span></div>
              </el-card>
            </el-col>
            <el-col :span="8">
              <el-card shadow="hover" class="metric-card">
                <div class="metric-title">Rated Torque</div>
                <div class="metric-value">{{ results.torque }} <span class="unit">Nm</span></div>
              </el-card>
            </el-col>
            <el-col :span="8">
              <el-card shadow="hover" class="metric-card">
                <div class="metric-title">Est. Weight</div>
                <div class="metric-value">{{ results.weight }} <span class="unit">kg</span></div>
              </el-card>
            </el-col>
          </el-row>

          <!-- Bottom: Canvas Visualizer -->
          <el-card class="viz-card">
             <template #header>
              <div class="card-header">
                <span>2D Cross Section (Auto-CAD)</span>
                <span class="viz-info">Zoom: {{ zoomLevel }}x</span>
              </div>
            </template>
            <div class="canvas-container">
              <canvas id="motorCanvas" width="800" height="600"></canvas>
            </div>
          </el-card>

        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted, watch, computed } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import { Document } from '@element-plus/icons-vue'
import { jsPDF } from "jspdf"

// --- State ---
const loading = ref(false)
const zoomLevel = ref(1.0)

const form = reactive({
  stator_od: 80,
  stack_length: 30,
  airgap: 0.7,
  turns_per_coil: 25,
  magnet_rem: 1.28,
  slot_pole_combo: '12N14P'
})

const results = reactive({
  kv: '-',
  torque: '-',
  weight: '-'
})

// --- Logic ---
const simulate = async () => {
  loading.value = true
  try {
    const response = await axios.post('http://127.0.0.1:8001/predict', form)
    const data = response.data
    results.kv = data.kv_rating
    results.torque = data.rated_torque
    results.weight = data.weight_kg
    ElMessage.success('Simulation Completed!')
  } catch (error) {
    console.error(error)
    ElMessage.error('Simulation Failed: Check Backend Connection')
  } finally {
    loading.value = false
  }
}

// --- Advanced Visualization ---
const drawMotor = () => {
  const canvas = document.getElementById('motorCanvas')
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  
  // Clear
  ctx.clearRect(0, 0, canvas.width, canvas.height)
  
  // Setup Geometry
  const cx = canvas.width / 2
  const cy = canvas.height / 2
  
  // Auto-scale to fit canvas
  const padding = 50
  const maxD = form.stator_od
  const scale = (Math.min(canvas.width, canvas.height) - padding * 2) / maxD
  zoomLevel.value = scale.toFixed(1)
  
  const r_od = (form.stator_od / 2) * scale
  // Assume Stator ID is 60% of OD
  const r_id = r_od * 0.6
  // Stator Yoke Thickness (approx 20% of radial thickness)
  const r_yoke = r_od - (r_od - r_id) * 0.2
  // Slot Bottom Radius
  const r_slot_bottom = r_yoke
  
  // Rotor
  const gap_scaled = form.airgap * scale * 2 // Exaggerate gap 2x for visibility
  const r_rotor_od = r_id - gap_scaled
  const r_rotor_id = r_rotor_od * 0.4 // Shaft
  
  // Parse Slots/Poles
  const match = form.slot_pole_combo.match(/(\d+)N(\d+)P/)
  const slots = match ? parseInt(match[1]) : 12
  const poles = match ? parseInt(match[2]) : 14
  
  // --- 1. Draw Stator Core (Gray) ---
  ctx.fillStyle = '#cbd5e1' // Light Gray Iron
  ctx.strokeStyle = '#64748b'
  ctx.lineWidth = 1
  
  // We need to draw the custom shape with teeth
  ctx.beginPath()
  // Outer Circle (CCW)
  ctx.arc(cx, cy, r_od, 0, 2 * Math.PI)
  
  // Inner "Teeth" (CW)
  // We'll construct a path for the inner boundary
  const slotPitch = (2 * Math.PI) / slots
  const toothWidthRatio = 0.5 // Tooth covers 50% of pitch
  const toothAngle = slotPitch * toothWidthRatio
  const slotAngle = slotPitch * (1 - toothWidthRatio)
  
  // To make a hole, we usually do sub-paths or use winding rules.
  // Simple approach: Draw Outer Circle, then draw White Slots on top? No, we want fill.
  // Let's use the evenodd rule or just draw the ring path fully.
  
  // Move to start of first tooth
  ctx.moveTo(cx + r_id, cy) 
  // We need to reverse the direction for the hole (CW) if using nonzero rule, 
  // but let's just draw the Stator Yoke Ring first, then Teeth.
  
  // Method B: Draw Yoke Ring
  ctx.beginPath()
  ctx.arc(cx, cy, r_od, 0, 2*Math.PI)
  ctx.arc(cx, cy, r_slot_bottom, 0, 2*Math.PI, true)
  ctx.fill()
  ctx.stroke()
  
  // Draw Teeth (Rectangles rotated)
  for (let i = 0; i < slots; i++) {
    const theta = i * slotPitch
    ctx.save()
    ctx.translate(cx, cy)
    ctx.rotate(theta)
    
    // Tooth is a rectangle from r_id to r_slot_bottom
    // Width? 
    const w_tooth = (2 * Math.PI * r_id / slots) * 0.5
    const h_tooth = r_slot_bottom - r_id
    
    ctx.fillStyle = '#cbd5e1'
    ctx.fillRect(r_id, -w_tooth/2, h_tooth, w_tooth)
    ctx.strokeRect(r_id, -w_tooth/2, h_tooth, w_tooth)
    
    // --- 2. Draw Windings (Copper) in Slots ---
  // Slot area is between teeth.
  // We draw "Coil Sides"
  const w_slot = (2 * Math.PI * r_id / slots) * 0.4 // Slightly smaller than slot pitch
  const h_coil = h_tooth * 0.8
    
    // Upper Coil Side
    ctx.fillStyle = '#b45309' // Copper
    // Positioned in the "Slot" gap. 
    // The current rotation is centered on a TOOTH. 
    // So the slot is at theta + slotPitch/2
    ctx.restore()
    
    ctx.save()
    ctx.translate(cx, cy)
    ctx.rotate(theta + slotPitch/2)
    
    // Draw two coil blocks in the slot
    // Block 1
    ctx.fillRect(r_id + 2, -w_slot/2 + 2, h_coil, w_slot/2 - 4)
    ctx.strokeRect(r_id + 2, -w_slot/2 + 2, h_coil, w_slot/2 - 4)
    // Block 2
    ctx.fillRect(r_id + 2, 2, h_coil, w_slot/2 - 4)
    ctx.strokeRect(r_id + 2, 2, h_coil, w_slot/2 - 4)
    
    ctx.restore()
  }
  
  // --- 3. Draw Rotor (Inner) ---
  ctx.beginPath()
  ctx.arc(cx, cy, r_rotor_od, 0, 2*Math.PI)
  ctx.fillStyle = '#94a3b8'
  ctx.fill()
  ctx.stroke()
  
  // Shaft
  ctx.beginPath()
  ctx.arc(cx, cy, r_rotor_id, 0, 2*Math.PI)
  ctx.fillStyle = '#f1f5f9' // White/Light
  ctx.fill()
  ctx.stroke()
  
  // --- 4. Draw Magnets ---
  for (let i = 0; i < poles; i++) {
    const theta = i * (2 * Math.PI / poles)
    ctx.save()
    ctx.translate(cx, cy)
    ctx.rotate(theta)
    
    const magH = (r_rotor_od - r_rotor_id) * 0.2
    const magW = (2 * Math.PI * r_rotor_od / poles) * 0.85
    
    // Surface mounted
    ctx.fillStyle = i % 2 === 0 ? '#ef4444' : '#3b82f6' // N=Red, S=Blue
    ctx.fillRect(r_rotor_od - magH, -magW/2, magH, magW)
    ctx.strokeRect(r_rotor_od - magH, -magW/2, magH, magW)
    
    // Label N/S
    ctx.fillStyle = 'white'
    ctx.font = '10px Arial'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillText(i % 2 === 0 ? 'N' : 'S', r_rotor_od - magH/2, 0)
    
    ctx.restore()
  }
  
  // --- 5. Dimensions Labels ---
  // Draw OD Arrow
  ctx.strokeStyle = '#000'
  ctx.fillStyle = '#000'
  ctx.lineWidth = 1
  
  // Horizontal Line for OD
  const y_dim = cy + r_od + 20
  ctx.beginPath()
  ctx.moveTo(cx - r_od, y_dim)
  ctx.lineTo(cx + r_od, y_dim)
  ctx.stroke()
  
  // Arrows
  ctx.beginPath()
  ctx.moveTo(cx - r_od, y_dim - 5); ctx.lineTo(cx - r_od, y_dim + 5);
  ctx.moveTo(cx + r_od, y_dim - 5); ctx.lineTo(cx + r_od, y_dim + 5);
  ctx.stroke()
  
  // Text
  ctx.font = '14px Arial'
  ctx.textAlign = 'center'
  ctx.fillText(`Stator OD: ${form.stator_od} mm`, cx, y_dim + 15)
  
  // ID Label
  ctx.fillText(`Stack: ${form.stack_length} mm`, cx, cy - r_od - 10)
}

// --- PDF Export ---
const exportReport = () => {
  const doc = new jsPDF()
  
  // Title
  doc.setFontSize(22)
  doc.setTextColor(40, 40, 40)
  doc.text("BLDC Motor Design Report", 20, 20)
  
  doc.setFontSize(12)
  doc.setTextColor(100)
  doc.text(`Generated on: ${new Date().toLocaleString()}`, 20, 30)
  
  // 1. Parameters Table
  doc.setDrawColor(0)
  doc.setFillColor(240, 240, 240)
  doc.rect(20, 40, 170, 10, 'F')
  doc.setFontSize(14)
  doc.setTextColor(0)
  doc.text("1. Design Inputs", 25, 47)
  
  doc.setFontSize(11)
  let y = 60
  const inputs = [
    `Stator OD: ${form.stator_od} mm`,
    `Stack Length: ${form.stack_length} mm`,
    `Airgap: ${form.airgap} mm`,
    `Turns per Coil: ${form.turns_per_coil}`,
    `Magnet Remanence: ${form.magnet_rem} T`,
    `Configuration: ${form.slot_pole_combo}`
  ]
  
  inputs.forEach(line => {
    doc.text(`• ${line}`, 30, y)
    y += 8
  })
  
  // 2. Performance Results
  y += 10
  doc.setFillColor(240, 240, 240)
  doc.rect(20, y, 170, 10, 'F')
  doc.setFontSize(14)
  doc.text("2. AI Performance Prediction", 25, y + 7)
  
  y += 20
  doc.setFontSize(12)
  doc.setTextColor(0, 100, 0) // Greenish
  doc.text(`Kv Rating: ${results.kv} RPM/V`, 30, y)
  doc.text(`Rated Torque: ${results.torque} Nm`, 30, y + 10)
  doc.text(`Estimated Weight: ${results.weight} kg`, 30, y + 20)
  
  // 3. Motor Image
  y += 40
  doc.setTextColor(0)
  doc.text("3. 2D Cross Section", 25, y)
  
  const canvas = document.getElementById('motorCanvas')
  if (canvas) {
    const imgData = canvas.toDataURL("image/png")
    // Add image (x, y, w, h)
    doc.addImage(imgData, 'PNG', 35, y + 10, 140, 105)
  }
  
  // Save
  doc.save(`BLDC_Design_${form.slot_pole_combo}.pdf`)
}

watch(form, drawMotor)
onMounted(drawMotor)

</script>

<style scoped>
.main-container { height: 100vh; background-color: #f8fafc; }
.header { background-color: #0f172a; color: white; padding: 0 2rem; height: 80px; display: flex; align-items: center; }
.header-content { display: flex; justify-content: space-between; width: 100%; align-items: center; }
.header h1 { margin: 0; font-size: 1.5rem; color: #f8fafc; }
.header p { margin: 0; opacity: 0.7; font-size: 0.85rem; }
.control-panel { padding: 20px; background: white; border-right: 1px solid #e2e8f0; }
.result-panel { padding: 20px; }
.unit { margin-left: 10px; color: #64748b; font-size: 0.8rem; }
.viz-card { margin-top: 20px; }
.canvas-container { display: flex; justify-content: center; background: #f1f5f9; padding: 20px; border-radius: 8px; }
.viz-info { float: right; font-size: 0.8rem; color: #64748b; }
.metric-value { font-size: 2rem; font-weight: bold; color: #0f172a; }
</style>
