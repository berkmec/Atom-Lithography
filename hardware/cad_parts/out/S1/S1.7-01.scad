// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S1.7-01)
// ============================================================================
// part_id           : S1.7-01
// parent_bom_id     : S1.7
// subsystem         : S1
// part_name         : S1-Multi Hizli-Degisim 3-Turlu Kaynak Kartus Yuvasi (31P Gaz / 121Sb 450C Firin / 167Er Mikro-Paul, Exp142 S1.6-01, 4.80 kg)
// material          : Ti-6Al-4V
// temp_stage        : 300 K (UHV kolon)
// vacuum_grade      : UHV 1e-9 mbar
// tolerance         : ±0.05 mm eksen
// computed_mass_kg  : 1.09537
// envelope_mm       : 76.000 x 101.000 x 95.000
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 76.0000;
bbox_y = 101.0000;
bbox_z = 95.0000;

// Part-specific parametric dimensions
bay_x = 76.0;
bay_y = 76.0;
bay_z = 95.0;
sb_oven_C = 450.0;
er_zpl_nm = 1536.0;

// Interface / port parameters (mm)
port_duoplasmatron_mate_cf40_od = 69.500;
port_duoplasmatron_mate_cf40_bore = 38.000;
port_duoplasmatron_mate_cf40_pcd = 58.700;
port_duoplasmatron_mate_cf40_bolts = 6;
port_oven_heater_feed_od = 16.000;

module part_S1_7_01() {
  difference() {
    union() {
      // ISO 3669 CF40 mounting flange to S1.1-01
      translate([0.000, -56.650, 0.000]) rotate([90.000, 0.000, 0.000]) {
        difference() {
          cylinder(d=69.500, h=12.700, center=true);
          cylinder(d=38.000, h=14.700, center=true);
          translate([0, 0, 5.100]) cylinder(d=48.100, h=1.750);
          for (i = [0 : 6 - 1])
            rotate([0, 0, i * 360 / 6])
              translate([29.350, 0, 0])
                cylinder(d=6.600, h=14.700, center=true);
        }
      }
      // Ti-6Al-4V quick-swap 3-species cartridge bay
      cube([76.000, 76.000, 95.000], center=true);
      // PBN 450 C 121Sb effusion oven
      translate([0.000, 4.000, -16.000]) rotate([90.000, 0.000, 0.000]) {
        difference() {
          cylinder(d=22.000, h=44.000, center=true);
          cylinder(d=16.000, h=46.000, center=true);
        }
      }
    }
    // Vapor/ion exit aperture
    translate([0.000, -35.000, 0.000]) rotate([90.000, 0.000, 0.000]) cylinder(d=34.000, h=14.000, center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([0.000, 110.000, 492.660]) rotate([0.000, 0.000, 0.000]) part_S1_7_01();

part_S1_7_01();
