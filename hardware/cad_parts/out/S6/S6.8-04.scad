// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S6.8-04)
// ============================================================================
// part_id           : S6.8-04
// parent_bom_id     : S6.8
// subsystem         : S6
// part_name         : Dis vakum kabi (OVC), dogrudan-gorus demet portu ve titresim-izole DR cercevesi
// material          : 316LN
// temp_stage        : 300 K
// vacuum_grade      : Kriyo-vakum / UHV
// tolerance         : ±0.2 mm
// computed_mass_kg  : 126.12750
// envelope_mm       : 390.000 x 393.000 x 985.000
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 390.0000;
bbox_y = 393.0000;
bbox_z = 985.0000;

// Part-specific parametric dimensions
ovc_id = 334.0;
ovc_od = 350.0;
top_flange_od = 390.0;
relief_dn = 50;

// Interface / port parameters (mm)
port_asme_rupture_disk_port_od = 75.000;
port_asme_rupture_disk_port_bore = 50.000;
port_asme_rupture_disk_port_bolts = 4;
port_bridge_bellows_east_od = 152.000;
port_bridge_bellows_east_bore = 76.000;
port_bridge_bellows_east_pcd = 130.200;
port_bridge_bellows_east_bolts = 16;
port_option_q_west_od = 113.500;
port_option_q_west_bore = 63.500;
port_option_q_west_pcd = 92.100;
port_option_q_west_bolts = 8;
port_pt420_top_port_od = 180.000;
port_pt420_top_port_bore = 92.000;
port_pt420_top_port_bolts = 4;

module part_S6_8_04() {
  difference() {
    union() {
      // DR vibration-isolated support frame
      translate([0.000, 0.000, -420.500]) cube([340.000, 340.000, 159.000], center=true);
      // 316LN DR OVC vessel
      translate([0.000, 0.000, 67.500]) {
        difference() {
          cylinder(d=350.000, h=785.000, center=true);
          cylinder(d=334.000, h=787.000, center=true);
        }
      }
      // Top 300 K main flange
      translate([0.000, 0.000, 472.500]) {
        difference() {
          cylinder(d=390.000, h=25.000, center=true);
          cylinder(d=92.000, h=27.000, center=true);
        }
      }
      // ASME DN50 ISO-K rupture-disk nozzle for S7.SAFETY-05
      translate([0.000, 186.000, 320.000]) rotate([-90.000, 0.000, 0.000]) cylinder(d=75.000, h=24.000, center=true);
    }
    // 24x M8 top flange bolts
    translate([0.000, 0.000, 472.500]) {
      for (i = [0 : 24 - 1])
        rotate([0, 0, i * 360 / 24])
          translate([184.000, 0, 0])
            cylinder(d=8.400, h=28.000, center=true);
    }
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([-650.000, 0.000, 500.000]) rotate([0.000, 0.000, 0.000]) part_S6_8_04();

part_S6_8_04();
