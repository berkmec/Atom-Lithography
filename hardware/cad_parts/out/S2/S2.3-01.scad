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
// computed_mass_kg  : 0.00890
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
e1_t_mm = 0.1;
gap12_mm = 0.9;
e2_t_mm = 0.16;
gap23_mm = 0.4;
e3_t_mm = 0.1;
stack_h_mm = 1.76;
wd_mm = 0.25;
v_e1_V = -5000.0;
v_e2_focus_V = 3734.61;
v_e3_V = 0.0;
e_gap_MV_m = 9.71;
focus_error_um = 0.005;

// Interface / port parameters (mm)
port_wafer_facing_wd_od = 60.000;
port_wafer_facing_wd_bore = 22.627;
port_minilens_top_od = 60.000;
port_minilens_top_bore = 22.627;

module part_S2_3_01() {
  difference() {
    union() {
      // Wafer 1 (E3): 0 V ground immersion electrode (t=0.100 mm)
      translate([0.000, 0.000, -0.830]) cylinder(d=60.000, h=0.100, center=true);
      // Pyrex/SiO2 anodic bond spacer 1 (gap23=0.400 mm, 9.34 MV/m)
      translate([0.000, 0.000, -0.580]) {
        difference() {
          cylinder(d=58.000, h=0.396, center=true);
          cylinder(d=28.000, h=2.396, center=true);
        }
      }
      // Wafer 2 (E2): +3734.6 V focus electrode (t=0.160 mm)
      translate([0.000, 0.000, -0.300]) cylinder(d=60.000, h=0.160, center=true);
      // Pyrex/SiO2 anodic bond spacer 2 (gap12=0.900 mm, 9.71 MV/m < 10 MV/m)
      translate([0.000, 0.000, 0.230]) {
        difference() {
          cylinder(d=58.000, h=0.896, center=true);
          cylinder(d=28.000, h=2.896, center=true);
        }
      }
      // Wafer 3 (E1): -5000 V entrance electrode (t=0.100 mm)
      translate([0.000, 0.000, 0.730]) cylinder(d=60.000, h=0.100, center=true);
      // Upper field-free entrance seating rim
      translate([0.000, 0.000, 0.831]) {
        difference() {
          cylinder(d=60.000, h=0.098, center=true);
          cylinder(d=28.000, h=2.098, center=true);
        }
      }
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
