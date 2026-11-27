// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S5.1-03)
// ============================================================================
// part_id           : S5.1-03
// parent_bom_id     : S5.1
// subsystem         : S5
// part_name         : Hizli giris yuk kilidi (load-lock) odasi ve CF100 tam-metal surgu vana
// material          : 316LN
// temp_stage        : 300 K
// vacuum_grade      : UHV 1e-8 mbar
// tolerance         : He <=1e-10 mbar*L/s
// computed_mass_kg  : 25.56413
// envelope_mm       : 413.725 x 369.430 x 690.789
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 413.7252;
bbox_y = 369.4296;
bbox_z = 690.7887;

// Part-specific parametric dimensions
cube_x = 180.0;
cube_y = 180.0;
cube_z = 170.0;
opt_elev_deg = 36.0;
stand_clear_granite = 15.0;

// Interface / port parameters (mm)
port_main_chamber_gate_in_od = 152.000;
port_main_chamber_gate_in_bore = 101.600;
port_main_chamber_gate_in_pcd = 130.200;
port_main_chamber_gate_in_bolts = 16;
port_vat_bonnet_top_cf100_od = 152.000;
port_vat_bonnet_top_cf100_bore = 68.000;
port_vat_bonnet_top_cf100_pcd = 130.200;
port_vat_bonnet_top_cf100_bolts = 16;
port_mbe_top_cf100_od = 152.000;
port_mbe_top_cf100_bore = 101.600;
port_mbe_top_cf100_pcd = 130.200;
port_mbe_top_cf100_bolts = 16;
port_transfer_arm_pos_x_od = 152.000;
port_transfer_arm_pos_x_bore = 101.600;
port_transfer_arm_pos_x_pcd = 130.200;
port_transfer_arm_pos_x_bolts = 16;
port_operator_door_neg_y_od = 152.000;
port_operator_door_neg_y_bore = 80.000;
port_operator_door_neg_y_pcd = 130.200;
port_operator_door_neg_y_bolts = 16;
port_n2_vent_neg_y_od = 33.800;
port_n2_vent_neg_y_bore = 16.000;
port_n2_vent_neg_y_pcd = 27.000;
port_n2_vent_neg_y_bolts = 6;
port_roughing_kf25_pos_y_od = 40.000;
port_roughing_kf25_pos_y_bore = 25.000;
port_port_808nm_flash_inclined_90_od = 113.500;
port_port_808nm_flash_inclined_90_bore = 44.000;
port_port_808nm_flash_inclined_90_pcd = 92.100;
port_port_808nm_flash_inclined_90_bolts = 8;
port_port_rta_flash_inclined_42_od = 152.000;
port_port_rta_flash_inclined_42_bore = 88.000;
port_port_rta_flash_inclined_42_pcd = 130.200;
port_port_rta_flash_inclined_42_bolts = 16;
port_port_pyro_inclined_238_od = 69.500;
port_port_pyro_inclined_238_bore = 28.000;
port_port_pyro_inclined_238_pcd = 58.700;
port_port_pyro_inclined_238_bolts = 6;
port_port_shutter_320_od = 69.500;
port_port_shutter_320_bore = 38.000;
port_port_shutter_320_pcd = 58.700;
port_port_shutter_320_bolts = 6;

module part_S5_1_03() {
  difference() {
    union() {
      // Inlet CF100 flange mating S5.1-01
      translate([-159.600, 0.000, 0.000]) rotate([0.000, -90.000, 0.000]) {
        difference() {
          cylinder(d=152.000, h=19.800, center=true);
          cylinder(d=101.600, h=21.800, center=true);
          translate([0, 0, 8.650]) cylinder(d=120.500, h=1.750);
          for (i = [0 : 16 - 1])
            rotate([0, 0, i * 360 / 16])
              translate([65.100, 0, 0])
                cylinder(d=8.400, h=21.800, center=true);
        }
      }
      // VAT CF100 all-metal gate valve body (bored Ø101.6)
      translate([-130.000, 0.000, 0.000]) cube([39.000, 172.000, 172.000], center=true);
      // Top CF100 VAT bonnet flange mating S7.SAFETY-06 (Z=658.2 mm)
      translate([-130.000, 0.000, 148.300]) {
        difference() {
          cylinder(d=152.000, h=19.800, center=true);
          cylinder(d=101.600, h=21.800, center=true);
          translate([0, 0, 8.650]) cylinder(d=120.500, h=1.750);
          for (i = [0 : 16 - 1])
            rotate([0, 0, i * 360 / 16])
              translate([65.100, 0, 0])
                cylinder(d=8.400, h=21.800, center=true);
        }
      }
      // Perforated load-lock chamber cube
      translate([0.000, 0.000, -9.800]) cube([180.000, 180.000, 150.000], center=true);
      // +Z CF100 MBE capper port (Z=585.0 mm)
      translate([0.000, 0.000, 75.100]) {
        difference() {
          cylinder(d=152.000, h=19.800, center=true);
          cylinder(d=101.600, h=21.800, center=true);
          translate([0, 0, 8.650]) cylinder(d=120.500, h=1.750);
          for (i = [0 : 16 - 1])
            rotate([0, 0, i * 360 / 16])
              translate([65.100, 0, 0])
                cylinder(d=8.400, h=21.800, center=true);
        }
      }
      // +X CF100 transfer arm port
      translate([80.100, 0.000, 0.000]) rotate([0.000, 90.000, 0.000]) {
        difference() {
          cylinder(d=152.000, h=19.800, center=true);
          cylinder(d=101.600, h=21.800, center=true);
          translate([0, 0, 8.650]) cylinder(d=120.500, h=1.750);
          for (i = [0 : 16 - 1])
            rotate([0, 0, i * 360 / 16])
              translate([65.100, 0, 0])
                cylinder(d=8.400, h=21.800, center=true);
        }
      }
      // -Y quick-access viewport door
      translate([0.000, -100.200, 0.000]) rotate([90.000, 0.000, 0.000]) {
        difference() {
          cylinder(d=152.000, h=19.800, center=true);
          cylinder(d=80.000, h=21.800, center=true);
          translate([0, 0, 8.650]) cylinder(d=120.500, h=1.750);
          for (i = [0 : 16 - 1])
            rotate([0, 0, i * 360 / 16])
              translate([65.100, 0, 0])
                cylinder(d=8.400, h=21.800, center=true);
        }
      }
      // Decoupled floor support stand
      translate([65.000, 0.000, -292.750]) cube([50.000, 150.000, 414.500], center=true);
    }
    // Wafer transfer through-bore
    translate([-40.000, 0.000, 0.000]) rotate([0.000, 90.000, 0.000]) cylinder(d=101.600, h=260.000, center=true);
    // Open +Z MBE evaporant beam bore
    translate([0.000, 0.000, 70.000]) cylinder(d=101.600, h=40.000, center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([420.000, 0.000, 500.000]) rotate([0.000, 0.000, 0.000]) part_S5_1_03();

part_S5_1_03();
