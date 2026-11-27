// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S1.3-01)
// ============================================================================
// part_id           : S1.3-01
// parent_bom_id     : S1.3
// subsystem         : S1
// part_name         : 5-20 keV ana hizlandirma/yavaslatma seramik kolon tupu
// material          : 316LN
// temp_stage        : 300 K
// vacuum_grade      : UHV 1e-9 mbar
// tolerance         : ±0.02 mm eksen
// computed_mass_kg  : 5.86447
// envelope_mm       : 175.000 x 152.000 x 216.300
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 175.0000;
bbox_y = 152.0000;
bbox_z = 216.3000;

// Part-specific parametric dimensions
cf_size = "CF100";
lower_z_canon_mm = 705.0;
spool_id = 112.0;
bore_id = 88.0;
hv_rating_kV = 25.0;
bakeout_C = 150.0;

// Interface / port parameters (mm)
port_lower_cf100_od = 152.000;
port_lower_cf100_bore = 112.000;
port_lower_cf100_pcd = 130.200;
port_lower_cf100_bolts = 16;
port_wien_slit_port_pos_y_od = 33.800;
port_wien_slit_port_pos_y_bore = 16.600;
port_wien_slit_port_pos_y_pcd = 27.000;
port_wien_slit_port_pos_y_bolts = 6;
port_wien_slit_port_neg_y_od = 33.800;
port_wien_slit_port_neg_y_bore = 16.600;
port_wien_slit_port_neg_y_pcd = 27.000;
port_wien_slit_port_neg_y_bolts = 6;
port_faraday_port_pos_x_od = 69.500;
port_faraday_port_pos_x_bore = 29.000;
port_faraday_port_pos_x_pcd = 58.700;
port_faraday_port_pos_x_bolts = 6;
port_faraday_port_neg_x_od = 69.500;
port_faraday_port_neg_x_bore = 29.000;
port_faraday_port_neg_x_pcd = 58.700;
port_faraday_port_neg_x_bolts = 6;
port_upper_ti_collar_od = 126.000;
port_upper_ti_collar_bore = 88.000;
port_upper_ti_collar_pcd = 112.000;
port_upper_ti_collar_bolts = 12;

module part_S1_3_01() {
  difference() {
    union() {
      // Lower ISO 3669 CF100 mating flange at Z_canon=705.0 mm
      translate([0.000, 0.000, -98.250]) rotate([180.000, 0.000, 0.000]) {
        difference() {
          cylinder(d=152.000, h=19.800, center=true);
          cylinder(d=112.000, h=21.800, center=true);
          translate([0, 0, 8.650]) cylinder(d=120.500, h=1.750);
          for (i = [0 : 16 - 1])
            rotate([0, 0, i * 360 / 16])
              translate([65.100, 0, 0])
                cylinder(d=8.400, h=21.800, center=true);
        }
      }
      // 316LN UHV Wien & slit enclosure spool
      translate([0.000, 0.000, -16.000]) {
        difference() {
          cylinder(d=121.000, h=144.500, center=true);
          cylinder(d=112.000, h=146.500, center=true);
        }
      }
      // Upper HV transition CF100 Ti-6Al-4V flange
      translate([0.000, 0.000, 66.250]) rotate([180.000, 0.000, 0.000]) {
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
      translate([0.000, 0.000, 87.250]) {
        difference() {
          cylinder(d=121.000, h=21.800, center=true);
          cylinder(d=88.000, h=23.800, center=true);
        }
      }
      // Brazed Ti-6Al-4V upper collar
      translate([0.000, 0.000, 103.300]) {
        difference() {
          cylinder(d=126.000, h=9.700, center=true);
          cylinder(d=88.000, h=11.700, center=true);
        }
      }
    }
    // 12xM6 upper collar bolts
    translate([0.000, 0.000, 103.300]) {
      for (i = [0 : 12 - 1])
        rotate([0, 0, i * 360 / 12])
          translate([56.000, 0, 0])
            cylinder(d=6.600, h=14.000, center=true);
    }
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([0.000, 0.000, 313.150]) rotate([0.000, 0.000, 0.000]) part_S1_3_01();

part_S1_3_01();
