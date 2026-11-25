// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S1.3-01)
// ============================================================================
// part_id           : S1.3-01
// parent_bom_id     : S1.3
// subsystem         : S1
// part_name         : 5-20 keV ana hizlandirma/yavaslatma seramik kolon tupu
// material          : Al2O3
// temp_stage        : 300 K
// vacuum_grade      : UHV 1e-9 mbar
// tolerance         : ±0.02 mm eksen
// computed_mass_kg  : 1.44216
// envelope_mm       : 152.000 x 152.000 x 51.800
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 152.0000;
bbox_y = 152.0000;
bbox_z = 51.8000;

// Part-specific parametric dimensions
cf_size = "CF100";
bore_id = 88.0;
hv_rating_kV = 25.0;
bakeout_C = 150.0;

// Interface / port parameters (mm)
port_lower_cf100_od = 152.000;
port_lower_cf100_bore = 88.000;
port_lower_cf100_pcd = 130.200;
port_lower_cf100_bolts = 16;
port_upper_ti_collar_od = 126.000;
port_upper_ti_collar_bore = 88.000;
port_upper_ti_collar_pcd = 112.000;
port_upper_ti_collar_bolts = 12;

module part_S1_3_01() {
  difference() {
    union() {
      // ISO 3669 CF100 Ti-6Al-4V base flange
      translate([0.000, 0.000, -16.000]) rotate([180.000, 0.000, 0.000]) {
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
      // Ribbed 25 kV Al2O3 HV ceramic break
      translate([0.000, 0.000, 5.000]) {
        difference() {
          cylinder(d=121.000, h=21.800, center=true);
          cylinder(d=88.000, h=23.800, center=true);
        }
      }
      // Brazed Ti-6Al-4V upper collar
      translate([0.000, 0.000, 21.050]) {
        difference() {
          cylinder(d=126.000, h=9.700, center=true);
          cylinder(d=88.000, h=11.700, center=true);
        }
      }
    }
    // 12xM6 upper collar bolts
    translate([0.000, 0.000, 21.050]) {
      for (i = [0 : 12 - 1])
        rotate([0, 0, i * 360 / 12])
          translate([56.000, 0, 0])
            cylinder(d=6.600, h=14.000, center=true);
    }
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([0.000, 0.000, 395.400]) rotate([0.000, 0.000, 0.000]) part_S1_3_01();

part_S1_3_01();
