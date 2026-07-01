---
name: BioPrecision SCADA
colors:
  surface: '#f4fbfa'
  surface-dim: '#d4dbdb'
  surface-bright: '#f4fbfa'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#eef5f4'
  surface-container: '#e8efee'
  surface-container-high: '#e2eae9'
  surface-container-highest: '#dde4e3'
  on-surface: '#161d1d'
  on-surface-variant: '#434750'
  inverse-surface: '#2b3231'
  inverse-on-surface: '#ebf2f1'
  outline: '#747781'
  outline-variant: '#c4c6d1'
  surface-tint: '#3d5e99'
  primary: '#00295d'
  on-primary: '#ffffff'
  primary-container: '#1b4079'
  on-primary-container: '#8daded'
  inverse-primary: '#acc7ff'
  secondary: '#546524'
  on-secondary: '#ffffff'
  secondary-container: '#d4e898'
  on-secondary-container: '#586928'
  tertiary: '#00303a'
  on-tertiary: '#ffffff'
  tertiary-container: '#124754'
  on-tertiary-container: '#85b5c4'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#d7e2ff'
  primary-fixed-dim: '#acc7ff'
  on-primary-fixed: '#001a40'
  on-primary-fixed-variant: '#22467f'
  secondary-fixed: '#d7eb9b'
  secondary-fixed-dim: '#bbcf81'
  on-secondary-fixed: '#161f00'
  on-secondary-fixed-variant: '#3d4c0d'
  tertiary-fixed: '#baeafa'
  tertiary-fixed-dim: '#9ecedd'
  on-tertiary-fixed: '#001f27'
  on-tertiary-fixed-variant: '#1a4d5a'
  background: '#f4fbfa'
  on-background: '#161d1d'
  surface-variant: '#dde4e3'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  headline-sm:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  label-lg:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 20px
    letterSpacing: 0.02em
  label-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.05em
  mono-data:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  unit: 8px
  container-padding: 24px
  gutter: 16px
  sidebar-width: 280px
  panel-gap: 20px
---

## Brand & Style
The design system is engineered for high-stakes industrial monitoring, specifically the nuanced detection of biofuel chemical signatures via electronic nose technology. The brand personality is **technical, crystalline, and ultra-precise**, balancing the sterile nature of a laboratory with the organic origins of biofuel.

The visual style utilizes a **Refined Glassmorphism** approach. It avoids the heavy clutter of traditional SCADA interfaces by using high-transparency frosted layers over a soft, breathable base. The aesthetic response should be one of "clinical clarity"—where critical gas chromatography data and quality grades are immediately legible against a vibrant, light-filled environment.

## Colors
The palette is anchored by a **Deep Navy (#1B4079)** for structural elements like sidebars and headers, providing a heavy weight that grounds the otherwise light interface. The background is a "Breathable White" with a slight mint tint to reduce eye strain during long monitoring shifts.

**Functional Accents:**
- **Lime Sage (#CBDF90):** Used for "Active State" indicators and E-Nose sensor pulses.
- **Teal (#4D7C8A):** Used for secondary navigation and data visualizations.
- **Status Tiers:** Grade A (Optimal) uses Vivid Green; Grade B (Warning) uses Orange-Amber; Grade C (Critical/Fail) uses Vivid Red.

Use gradients sparingly, primarily within glass panels to simulate depth using the Sage and Pale Teal values.

## Typography
This design system relies exclusively on **Inter** to maintain a systematic and utilitarian feel. The hierarchy is strictly enforced to ensure that sensor readings (numerical data) are distinguished from UI labels.

- **Headlines:** Use Bold weights with slight negative letter spacing for a dense, authoritative look.
- **Data Tables:** Use `mono-data` (Inter with tabular figures enabled) for sensor telemetry to prevent "jumping" text during real-time updates.
- **Labels:** Use `label-sm` in All Caps for non-interactive metadata and sensor unit descriptions.

## Layout & Spacing
The layout follows a **Fixed-Fluid Hybrid** model. The sidebar is fixed at 280px, while the main dashboard area uses a 12-column fluid grid to accommodate complex data visualizations.

- **Rhythm:** Use an 8px base grid. All margins and paddings must be multiples of 8.
- **Density:** High density is permitted for data tables, but "Action Cards" (containing E-Nose triggers) must have generous 24px internal padding.
- **Breakpoints:** On tablet screens, the 12-column grid collapses to 6 columns, and the sidebar transforms into a bottom navigation bar.

## Elevation & Depth
Elevation is not conveyed through traditional black shadows, but through **Color-Tinted Diffusion** and **Backdrop Blurs**.

1.  **Level 0 (Base):** Soft White (#F8FFFE).
2.  **Level 1 (Panels):** Semi-transparent frosted glass (White @ 70% opacity) with a 20px background blur and a 1px solid border in Pale Teal.
3.  **Level 2 (Modals/Popovers):** Higher opacity glass with a soft, diffused shadow tinted with the Primary Navy color at 5% opacity.

Borders are critical: use "dual-tone" borders (Teal on top/left, Sage on bottom/right) for active sensor modules to create a subtle 3D technical feel without skeuomorphism.

## Shapes
The shape language is **"Geometric Organic."** While the system uses a standard `Rounded` (0.5rem) corner for most containers, specific elements related to the "Nose" or "Gas Flow" should utilize fully rounded pill shapes.

- **Data Cards:** 1rem (rounded-lg) to soften the technical data.
- **Input Fields:** 0.5rem (base roundedness).
- **Status Pills:** Fully rounded (pill-shaped) to represent droplets or gas particles.

## Components
- **Buttons:** Primary buttons use the Deep Navy background with white text. Secondary buttons are "Ghost" style with a Teal border.
- **E-Nose Indicators:** Round status lights with a "Pulse" animation. When a grade is detected (A, B, or C), the indicator should glow with a 15px outer blur in the respective semantic color.
- **Data Cards:** Use a glassmorphic background. Headlines should be in Navy, while the primary metric (e.g., Ethanol %) should be in the display-lg size.
- **Input Fields:** Flat white background with a 1px Teal border. On focus, the border transitions to Lime Green with a 4px soft outer glow.
- **Charts:** Line charts should use smooth bezier curves rather than jagged lines to reinforce the organic nature of biofuel. Use Sage and Teal for the data paths.