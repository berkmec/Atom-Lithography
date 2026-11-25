// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S2.3-01)
// ============================================================================
// part_id           : S2.3-01
// parent_bom_id     : S2.3
// subsystem         : S2
// part_name         : Cok-aciklikli elektrostatik mini-lens dizisi (Arch-B 0.50 mm, 32x32=1024, Exp124)
// material          : Si
// temp_stage        : 300 K
// vacuum_grade      : UHV 1e-9 mbar
// tolerance         : ±50 nm delik yuvarlakligi
// computed_mass_kg  : 0.00989
// envelope_mm       : 60.000 x 60.000 x 1.760
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 60.0000;
bbox_y = 60.0000;
bbox_z = 1.7600;

// Part-specific parametric dimensions
nx = 32;
ny = 32;
pitch_mm = 0.5;
hole_d_mm = 0.3;
stack_h_mm = 1.76;
wd_mm = 0.25;
e_gap_MV_m = 10.6;

// Interface / port parameters (mm)
port_wafer_facing_wd_od = 60.000;
port_wafer_facing_wd_bore = 22.627;
port_minilens_top_od = 60.000;
port_minilens_top_bore = 22.627;

module part_S2_3_01() {
  difference() {
    union() {
      // Wafer 1: 0 V ground immersion electrode
      translate([0.000, 0.000, -0.710]) cylinder(d=60.000, h=0.340, center=true);
      // Pyrex/SiO2 anodic bond spacer 1
      translate([0.000, 0.000, -0.355]) {
        difference() {
          cylinder(d=58.000, h=0.350, center=true);
          cylinder(d=28.000, h=2.350, center=true);
        }
      }
      // Wafer 2: 1.3 keV retarding focus electrode
      translate([0.000, 0.000, 0.010]) cylinder(d=60.000, h=0.360, center=true);
      // Pyrex/SiO2 anodic bond spacer 2
      translate([0.000, 0.000, 0.365]) {
        difference() {
          cylinder(d=58.000, h=0.330, center=true);
          cylinder(d=28.000, h=2.330, center=true);
        }
      }
      // Wafer 3: 10 keV entrance electrode
      translate([0.000, 0.000, 0.710]) cylinder(d=60.000, h=0.340, center=true);
    }
    // 32x32 = 1,024 D=0.30 mm Arch-B lens bores
    for (ix = [0 : 32 - 1])
      for (iy = [0 : 32 - 1])
        translate([(ix - 15.500) * 0.5000, (iy - 15.500) * 0.5000, 0])
          cylinder(d=0.3000, h=2.200, center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([0.000, 0.000, 1.130]) rotate([0.000, 0.000, 0.000]) part_S2_3_01();

part_S2_3_01();
