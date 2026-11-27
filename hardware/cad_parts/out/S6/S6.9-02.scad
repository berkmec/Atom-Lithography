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
// computed_mass_kg  : 4.49325
// envelope_mm       : 185.000 x 152.000 x 152.000
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 185.0000;
bbox_y = 152.0000;
bbox_z = 152.0000;

// Part-specific parametric dimensions
bellows_id = 76.0;
bellows_od = 98.0;
l_active = 116.0;
n_convolutions = 28;
sheet_mm = 0.15;
k_n_per_m = 2000.0;

// Interface / port parameters (mm)
port_ovc_dr_cf100_od = 152.000;
port_ovc_dr_cf100_bore = 76.000;
port_ovc_dr_cf100_pcd = 130.200;
port_ovc_dr_cf100_bolts = 16;
port_uhv_chamber_cf100_od = 152.000;
port_uhv_chamber_cf100_bore = 76.000;
port_uhv_chamber_cf100_pcd = 130.200;
port_uhv_chamber_cf100_bolts = 16;

module part_S6_9_02() {
  union() {
    // 28-convolution 316L CF100 bellows envelope
    rotate([0.000, 90.000, 0.000]) {
      difference() {
        cylinder(d=98.000, h=116.000, center=true);
        cylinder(d=76.000, h=118.000, center=true);
      }
    }
    // DR-side ISO 3669 CF100 flange
    translate([-68.100, 0.000, 0.000]) rotate([0.000, -90.000, 0.000]) {
      difference() {
        cylinder(d=152.000, h=19.800, center=true);
        cylinder(d=76.000, h=21.800, center=true);
        translate([0, 0, 8.650]) cylinder(d=120.500, h=1.750);
        for (i = [0 : 16 - 1])
          rotate([0, 0, i * 360 / 16])
            translate([65.100, 0, 0])
              cylinder(d=8.400, h=21.800, center=true);
      }
    }
    // UHV-side ISO 3669 CF100 flange (X=-289.5 mm)
    translate([68.100, 0.000, 0.000]) rotate([0.000, 90.000, 0.000]) {
      difference() {
        cylinder(d=152.000, h=19.800, center=true);
        cylinder(d=76.000, h=21.800, center=true);
        translate([0, 0, 8.650]) cylinder(d=120.500, h=1.750);
        for (i = [0 : 16 - 1])
          rotate([0, 0, i * 360 / 16])
            translate([65.100, 0, 0])
              cylinder(d=8.400, h=21.800, center=true);
      }
    }
    // DR-side CF100 weld-neck spool
    translate([-92.600, 0.000, 0.000]) rotate([0.000, 90.000, 0.000]) {
      difference() {
        cylinder(d=84.000, h=28.800, center=true);
        cylinder(d=76.000, h=30.800, center=true);
      }
    }
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([-367.500, 0.000, 493.500]) rotate([0.000, 0.000, 0.000]) part_S6_9_02();

part_S6_9_02();
