// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S6.9-02)
// ============================================================================
// part_id           : S6.9-02
// parent_bom_id     : S6.9
// subsystem         : S6
// part_name         : Kenar-kaynakli 316L CF63 OVC/UHV ayrilma korugu (s6_cryo_bridge_ovc, k=2000 N/m, Exp133)
// material          : 316L
// temp_stage        : 300 K
// vacuum_grade      : UHV 1e-9 mbar
// tolerance         : ±10% yay sabiti
// computed_mass_kg  : 2.64067
// envelope_mm       : 200.500 x 113.500 x 113.500
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 200.5000;
bbox_y = 113.5000;
bbox_z = 113.5000;

// Part-specific parametric dimensions
bellows_id = 44.0;
bellows_od = 68.0;
l_active = 120.0;
n_convolutions = 28;
sheet_mm = 0.15;
k_n_per_m = 2000.0;

// Interface / port parameters (mm)
port_ovc_dr_cf63_od = 113.500;
port_ovc_dr_cf63_bore = 44.000;
port_ovc_dr_cf63_pcd = 92.100;
port_ovc_dr_cf63_bolts = 8;
port_uhv_chamber_cf63_od = 113.500;
port_uhv_chamber_cf63_bore = 44.000;
port_uhv_chamber_cf63_pcd = 92.100;
port_uhv_chamber_cf63_bolts = 8;

module part_S6_9_02() {
  union() {
    // 28-convolution 316L bellows envelope
    rotate([0.000, 90.000, 0.000]) {
      difference() {
        cylinder(d=68.000, h=120.000, center=true);
        cylinder(d=44.000, h=122.000, center=true);
      }
    }
    // DR-side ISO 3669 CF63 flange
    translate([-68.950, 0.000, 0.000]) rotate([0.000, -90.000, 0.000]) {
      difference() {
        cylinder(d=113.500, h=17.500, center=true);
        cylinder(d=44.000, h=19.500, center=true);
        translate([0, 0, 7.500]) cylinder(d=82.400, h=1.750);
        for (i = [0 : 8 - 1])
          rotate([0, 0, i * 360 / 8])
            translate([46.050, 0, 0])
              cylinder(d=8.400, h=19.500, center=true);
      }
    }
    // UHV-side ISO 3669 CF63 flange (X=-274.0 mm)
    translate([69.250, 0.000, 0.000]) rotate([0.000, 90.000, 0.000]) {
      difference() {
        cylinder(d=113.500, h=17.500, center=true);
        cylinder(d=44.000, h=19.500, center=true);
        translate([0, 0, 7.500]) cylinder(d=82.400, h=1.750);
        for (i = [0 : 8 - 1])
          rotate([0, 0, i * 360 / 8])
            translate([46.050, 0, 0])
              cylinder(d=8.400, h=19.500, center=true);
      }
    }
    // DR-side CF63 weld-neck spool
    translate([-100.200, 0.000, 0.000]) rotate([0.000, 90.000, 0.000]) {
      difference() {
        cylinder(d=52.000, h=44.600, center=true);
        cylinder(d=44.000, h=46.600, center=true);
      }
    }
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([-352.000, 0.000, 493.500]) rotate([0.000, 0.000, 0.000]) part_S6_9_02();

part_S6_9_02();
