// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S4.5-02)
// ============================================================================
// part_id           : S4.5-02
// parent_bom_id     : S4.5
// subsystem         : S4
// part_name         : Yonga referans isareti (fiducial) hizalama optigi ve karanlik-alan kamera
// material          : 316LN
// temp_stage        : 300 K
// vacuum_grade      : UHV / Viewport
// tolerance         : ±1 nm
// computed_mass_kg  : 0.93707
// envelope_mm       : 106.017 x 110.070 x 69.236
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 106.0170;
bbox_y = 110.0700;
bbox_z = 69.2355;

// Part-specific parametric dimensions
azimuth_deg = 50.0;
z_mount_mm = 60.0;
cf40_od_mm = 69.5;
clear_aperture_mm = 32.0;

// Interface / port parameters (mm)
port_fiducial_cf40_viewport_od = 69.500;
port_fiducial_cf40_viewport_bore = 32.000;
port_fiducial_cf40_viewport_pcd = 58.700;
port_fiducial_cf40_viewport_bolts = 6;

module part_S4_5_02() {
  union() {
    // ISO 3669 CF40 fiducial microscope viewport
    translate([142.924, 170.330, 0.000]) rotate([0.000, -90.000, 50.000]) {
      difference() {
        cylinder(d=69.500, h=12.700, center=true);
        cylinder(d=32.000, h=14.700, center=true);
        translate([0, 0, 5.100]) cylinder(d=48.100, h=1.750);
        for (i = [0 : 6 - 1])
          rotate([0, 0, i * 360 / 6])
            translate([29.350, 0, 0])
              cylinder(d=6.600, h=14.700, center=true);
      }
    }
    // Long-WD objective & dark-field ring illuminator
    translate([159.733, 190.362, 0.000]) rotate([0.000, 90.000, 50.000]) cylinder(d=44.000, h=39.000, center=true);
    // Scientific CMOS dark-field camera head
    translate([186.087, 221.770, 0.000]) rotate([0.000, 0.000, 50.000]) cube([42.000, 54.000, 54.000], center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([0.000, 0.000, 60.000]) rotate([0.000, 0.000, 0.000]) part_S4_5_02();

part_S4_5_02();
