// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S5.3-02)
// ============================================================================
// part_id           : S5.3-02
// parent_bom_id     : S5.3
// subsystem         : S5
// part_name         : Safir / erimis-silika UHV tavlama optik penceresi ve odak aynalari
// material          : 316LN
// temp_stage        : 300 K
// vacuum_grade      : UHV 1e-9 mbar
// tolerance         : lambda/4
// computed_mass_kg  : 3.25134
// envelope_mm       : 78.000 x 152.000 x 152.000
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 78.0000;
bbox_y = 152.0000;
bbox_z = 152.0000;

// Part-specific parametric dimensions
clear_aperture_mm = 88.0;
window_d_mm = 96.0;
barrel_l_mm = 58.0;
elev_deg = 36.0;

// Interface / port parameters (mm)
port_chamber_cf100_mate_od = 152.000;
port_chamber_cf100_mate_bore = 88.000;
port_chamber_cf100_mate_pcd = 130.200;
port_chamber_cf100_mate_bolts = 16;
port_lamp_head_mount_od = 128.000;
port_lamp_head_mount_bore = 88.000;

module part_S5_3_02() {
  union() {
    // ISO 3669 CF100 UV-IR fused-silica viewport flange
    translate([9.900, 0.000, 0.000]) rotate([0.000, -90.000, 0.000]) {
      difference() {
        cylinder(d=152.000, h=19.800, center=true);
        cylinder(d=88.000, h=21.800, center=true);
        translate([0, 0, 8.650]) cylinder(d=120.500, h=1.750);
        for (i = [0 : 16 - 1])
          rotate([0, 0, i * 360 / 16])
            translate([65.100, 0, 0])
              cylinder(d=8.400, h=21.800, center=true);
      }
    }
    // UV-IR fused-silica optical window (>10 J/cm^2)
    translate([14.900, 0.000, 0.000]) rotate([0.000, 90.000, 0.000]) cylinder(d=96.000, h=10.000, center=true);
    // Focusing mirror barrel & baffle
    translate([49.000, 0.000, 0.000]) rotate([0.000, 90.000, 0.000]) {
      difference() {
        cylinder(d=116.000, h=58.000, center=true);
        cylinder(d=88.000, h=60.000, center=true);
      }
    }
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([548.322, -123.919, 629.607]) rotate([0.000, -36.000, 316.000]) part_S5_3_02();

part_S5_3_02();
