/*
This is annotated ethereal capture of a VIE client logging into ASSS and then leaving.
I removed most of the ACK's because they cluttered more than they revealed.
Packet names refer to their class in my libraries.
-div, Feb. 9, 2010
*/

char client_0[] = { /* core.packet.Connect
Connect:
.client_key = 0xd7d3bef7
.version = 0x0001    		*/
0x00, 0x01, 0xf7, 0xbe, 0xd3, 0xd7, 0x01, 0x00 };

char server_0[] = { /* core.packet.ConnectResponse
ConnectResponse
.server_key = 0x282c4109*/
0x00, 0x02, 0x09, 0x41, 0x2c, 0x28 };

char client_1[] = { /* core.packet.Reliable(game.c2s_packet.Login)
Reliable:
.seq: 0
>Login:
.is_new_user: 		0
.name: 			divtest1
.password: 		password
.machine_id: 		915817184
.connection_type: 	4
.time_zone_bias: 	300
.client_version: 	134
.memory_checksum0: 	444
.memory_checksum1: 	555
.permission_id: 	531149277   */
0x00, 0x03, 0xfd, 0x8b, 0xe2, 0xbb, 0x8b, 0x6b, 
0x0c, 0x33, 0xbc, 0x4a, 0x39, 0x7c, 0x7f, 0xc0, 
0x78, 0x58, 0xea, 0xf6, 0x14, 0xdb, 0x88, 0xb6, 
0x25, 0xcc, 0x3c, 0x29, 0xd4, 0xef, 0x9a, 0xf4, 
0xd7, 0x32, 0x24, 0x0b, 0xf5, 0x24, 0x7f, 0x3b, 
0x04, 0xa4, 0x9d, 0x97, 0x67, 0x0b, 0xf6, 0x7c, 
0xe2, 0xd8, 0x14, 0x91, 0x3d, 0x6c, 0x9d, 0x58, 
0x35, 0x06, 0x90, 0x1e, 0x8d, 0x39, 0xba, 0x96, 
0x48, 0xa8, 0xdc, 0xaf, 0x16, 0x26, 0xd6, 0x5d, 
0x54, 0xe2, 0xda, 0x6f, 0x23, 0x9f, 0x9f, 0x38, 
0xef, 0x26, 0x36, 0x6a, 0x87, 0x8e, 0xa6, 0xed, 
0x85, 0xce, 0x63, 0xed, 0x0b, 0x8f, 0x69, 0xac, 
0x98, 0x71, 0x23, 0xdf, 0xd9, 0x5a, 0x79, 0x05, 
0x88, 0x00, 0x1e };

char client_2[] = { /* core.packet.Sync
Sync:
.sender_time: 78699
.packets_sent: 3
.packets_received: 1     */
0x00, 0x05, 0x96, 0xb8, 0xe3, 0xbb, 0xea, 0x58, 
0x69, 0x5a, 0xaa, 0x0d, 0x39, 0x66 };

char server_1[] = { /* core.packet.SyncResponse
SyncResponse:
.remote_time: 78699
.sender_time: 2014830415 */
0x00, 0x06, 0x96, 0xb8, 0xe3, 0xbb, 0xa6, 0x87, 
0x7e, 0x22 };

char server_2[] = { /* core.packet.ReliableACK
ReliableACK:
.seq: 0              */
0x00, 0x04, 0xfd, 0x8b, 0xe2, 0xbb };

char server_3[] = { /* Reliable(game.s2c_packet.LoginResponse)
Reliable:
.seq: 0
>LoginResponse:
.response: 0
.server_version: 134
.is_vip: 0
.checksum_exe: 0xf1429ce8
.demographic_data: 0
.checksum_code: 0x281cc948
.checksum_news: 0xcc1c6195 */
0x00, 0x03, 0xfd, 0x8b, 0xe2, 0xbb, 0x88, 0x6b, 
0xee, 0x5a, 0xc9, 0x3e, 0xbe, 0x66, 0x7e, 0x85, 
0x17, 0xde, 0xa9, 0x42, 0x7b, 0x5d, 0xcb, 0x02, 
0x4a, 0x4a, 0x37, 0x54, 0xa7, 0x41, 0x04, 0xe8, 
0xb8, 0x50, 0xba, 0x17, 0x9a, 0x46, 0xe1, 0x27, 
0x1b, 0xa7 };

char client_4[] = { // Reliable(game.c2s_packet.ArenaLogin)
0x00, 0x03, 0xfc, 0x8b, 0xe2, 0xbb, 0x82, 0x6b, 
0x68, 0x5b, 0x43, 0x3c, 0xd8, 0x66, 0x0b, 0x78, 
0x99, 0x42, 0x9e, 0x4e, 0xf5, 0xc1, 0xfc, 0x0e, 
0xc4, 0xd6, 0x48, 0x91, 0x35, 0xf5, 0xee, 0x4c };

char server_5[] = { // Reliable(Chunk) of game.s2c_packet.ArenaSettings
0x00, 0x03, 0xff, 0x8b, 0xe2, 0xbb, 0x80, 0x63, 
0x67, 0x5b, 0xc1, 0x36, 0x97, 0x68, 0x76, 0x8d, 
0x12, 0x45, 0xe3, 0xbb, 0xa2, 0xc3, 0x7b, 0xfb, 
0xa4, 0xd4, 0xfd, 0x64, 0x79, 0xf6, 0x69, 0xb9, 
0x56, 0x2a, 0x41, 0x46, 0xa4, 0x3b, 0xca, 0x71, 
0x24, 0xda, 0xaf, 0xaf, 0x54, 0x1a, 0xfb, 0x21, 
0x19, 0xc9, 0xed, 0xcd, 0x98, 0x7c, 0x72, 0x04, 
0x3c, 0x1b, 0x6b, 0x47, 0x54, 0x23, 0x6a, 0xce, 
0x84, 0xb2, 0xa7, 0xfa, 0xc9, 0x39, 0x62, 0x0f, 
0x43, 0xbf, 0xfa, 0x0b, 0xca, 0xee, 0x18, 0x68, 
0x80, 0xd1, 0x01, 0x82, 0x79, 0x78, 0x29, 0x25, 
0x78, 0x38, 0x91, 0xf8, 0x59, 0xd1, 0xb8, 0xb9, 
0x5c, 0x2f, 0x8f, 0xca, 0x3d, 0x07, 0xe7, 0x10, 
0x75, 0x5d, 0xb5, 0xa7, 0x93, 0xbf, 0x67, 0x86, 
0xb9, 0x6c, 0xe6, 0xfa, 0xf2, 0x0b, 0x75, 0x89, 
0x5a, 0x61, 0xbf, 0x8b, 0xf9, 0x7d, 0x9e, 0xbf, 
0x97, 0xb0, 0x06, 0xf7, 0xef, 0xb2, 0x61, 0x10, 
0x6c, 0x7b, 0x84, 0xdb, 0x7a, 0x9f, 0xaa, 0x4f, 
0x2d, 0xf4, 0x62, 0x00, 0xaa, 0xfb, 0xe5, 0x8b, 
0x74, 0x72, 0x7b, 0xed, 0xc9, 0x27, 0xfb, 0x39, 
0x4d, 0x66, 0xad, 0x42, 0xbb, 0xe1, 0x07, 0xd2, 
0x2a, 0x52, 0x04, 0x2f, 0x39, 0xbc, 0x25, 0x39, 
0x2d, 0xea, 0x7c, 0x7f, 0xbc, 0x2f, 0x0b, 0x28, 
0xaa, 0x25, 0xa2, 0x51, 0x5b, 0x62, 0xea, 0xf4, 
0xa2, 0x14, 0xd3, 0x53, 0x4a, 0xc2, 0x23, 0x18, 
0x1a, 0xfc, 0x33, 0x81, 0x92, 0xab, 0xd6, 0x96, 
0xdb, 0xd1, 0x81, 0xc2, 0x9c, 0xc2, 0xd7, 0x88, 
0x8a, 0xf6, 0x3c, 0x51, 0x7e, 0x8f, 0xcb, 0x90, 
0x6c, 0x43, 0x34, 0xee, 0x11, 0x5a, 0x2a, 0x71, 
0xc3, 0x52, 0x10, 0x13, 0x02, 0x04, 0x2d, 0x62, 
0x9d, 0xc0, 0x94, 0x5f, 0x0b, 0xf1, 0xb7, 0x31, 
0xa2, 0xbc, 0x01, 0xe1, 0xe2, 0xe2, 0xae, 0x36, 
0x86, 0x95, 0xee, 0x56, 0x13, 0x5a, 0x43, 0x55, 
0x72, 0x7a, 0x8e, 0x26, 0x99, 0x7e, 0x26, 0x29, 
0x95, 0xff, 0x94, 0xa2, 0xb4, 0x9e, 0x44, 0xb5, 
0xb4, 0xc9, 0x05, 0x62, 0x38, 0xe1, 0xe4, 0x40, 
0xed, 0x05, 0x93, 0xc8, 0xee, 0x6f, 0x81, 0xda, 
0x1e, 0xea, 0x1b, 0xbe, 0xd9, 0x04, 0x46, 0xf1, 
0x9f, 0x9b, 0x13, 0xa6, 0xe0, 0x52, 0xa9, 0x48, 
0xa1, 0x60, 0xf4, 0x7f, 0x58, 0xf8, 0x21, 0xe6, 
0x2f, 0xb4, 0x26, 0x4e, 0xed, 0x68, 0xe4, 0x69, 
0x5f, 0xe7, 0xc1, 0x35, 0x96, 0xc4, 0xed, 0x63, 
0xa4, 0x13, 0x8f, 0xe8, 0x47, 0x97, 0xfa, 0x4a, 
0x50, 0xe8, 0x17, 0x31, 0x46, 0x5b, 0x1d, 0xd4, 
0xbc, 0x8b, 0xbe, 0x14, 0xad, 0x53, 0xe7, 0x52, 
0xb0, 0xa5, 0xc4, 0x7e, 0x7a, 0xee, 0x41, 0x27, 
0x5c, 0xf5, 0x8c, 0xbd, 0x41, 0xdc, 0xdc, 0xc1, 
0xa0, 0xe5, 0x76, 0x6b, 0xa3, 0xf4, 0xe9, 0x46, 
0xab, 0x1a, 0xf4, 0xad, 0x44, 0x39, 0x98, 0x55, 
0x50, 0x3c, 0x86, 0x9c, 0xe8, 0x73, 0x38, 0xd0, 
0x25, 0x15, 0x99, 0xc2, 0xc2, 0x90, 0x11, 0x4c, 
0xaa, 0x90, 0x7d, 0x21, 0xc4, 0x13, 0x7f, 0xf0, 
0xee, 0x91, 0x12, 0x02, 0xe5, 0x7f, 0x7a, 0xd3, 
0x48, 0xd4, 0x7d, 0xa2, 0xf4, 0xfa, 0x5b, 0x99, 
0x6f, 0xbc, 0x36, 0x03, 0x8d, 0x1d, 0x3c, 0x27, 
0x13, 0x34, 0x74, 0x46, 0xd9, 0xf0, 0x24, 0x8b, 
0x2d, 0xbd, 0xfc, 0x45, 0x3d, 0x5e, 0xec, 0x2b, 
0xc0, 0xd0, 0x54, 0xb1, 0x30, 0x00, 0xb7, 0xf2, 
0xb4, 0xf3, 0xd6, 0x6e, 0x40, 0xd3, 0x2e, 0xdf, 
0xf7, 0x18, 0x20, 0xee, 0xb4, 0x8e, 0x72, 0x0e, 
0xfb, 0x44, 0x5b, 0xae, 0x90, 0xf1, 0x6f, 0x3b };

char server_6[] = { // next Reliable(Chunk) of game.s2c_packet.ArenaSettings
0x00, 0x03, 0xfe, 0x8b, 0xe2, 0xbb, 0x81, 0x63, 
0x20, 0x57, 0xa5, 0x32, 0x78, 0x6c, 0xc3, 0x89, 
0x28, 0x48, 0x11, 0xb2, 0x20, 0xcf, 0x74, 0xf5, 
0x39, 0xd8, 0xc2, 0x6a, 0x32, 0xfb, 0xc2, 0xb7, 
0x55, 0x26, 0xcc, 0x4c, 0xf3, 0x33, 0x2f, 0x77, 
0x73, 0xd2, 0xc3, 0xa8, 0x7e, 0x12, 0xe8, 0x27, 
0x6d, 0xc1, 0x91, 0xca, 0x92, 0x76, 0x2a, 0x03, 
0x83, 0x1c, 0x12, 0x45, 0x0c, 0x23, 0xfc, 0xc4, 
0xc5, 0xb2, 0xda, 0xfd, 0x5f, 0x35, 0xd1, 0x03, 
0xfc, 0xb2, 0x49, 0x05, 0x8f, 0xe3, 0x0f, 0x67, 
0xa0, 0xdc, 0xa6, 0x89, 0xc9, 0x75, 0x36, 0x25, 
0xdd, 0xb7, 0x25, 0xfb, 0xe2, 0x5e, 0x30, 0xba, 
0x71, 0xa0, 0x7a, 0xc9, 0x30, 0x8b, 0x20, 0x13, 
0x61, 0xd1, 0x47, 0xa4, 0x10, 0x3c, 0x51, 0x8c, 
0xf2, 0xe6, 0x90, 0xf0, 0xa1, 0x8d, 0x66, 0x8f, 
0x24, 0xe6, 0x9a, 0x8f, 0xa1, 0xf8, 0x88, 0xba, 
0xe2, 0x34, 0x86, 0xf2, 0x16, 0x3d, 0xe9, 0x12, 
0xd0, 0x74, 0xe6, 0xd9, 0xa2, 0x90, 0xac, 0x4d, 
0x91, 0xfb, 0xf2, 0x02, 0x56, 0xf5, 0x65, 0x89, 
0x04, 0x76, 0x85, 0xeb, 0x8d, 0x3f, 0x3a, 0x3e, 
0xc2, 0x77, 0xe7, 0x4f, 0x4c, 0xf4, 0xd2, 0xd9, 
0xc9, 0x47, 0xfe, 0x24, 0x0c, 0xa8, 0x4b, 0x32, 
0x50, 0xff, 0x34, 0x70, 0x11, 0x3d, 0x2b, 0x2b, 
0x07, 0x37, 0x0b, 0x53, 0xb1, 0x70, 0x39, 0xf7, 
0x16, 0x06, 0xb5, 0x50, 0x38, 0xd3, 0x64, 0x1b, 
0xd1, 0xe2, 0x89, 0x82, 0xc2, 0xb8, 0x4c, 0x9c, 
0x96, 0xc2, 0xc5, 0xc7, 0xd2, 0xd8, 0x25, 0x8a, 
0xed, 0xed, 0xcd, 0x51, 0xe3, 0x94, 0x9e, 0x91, 
0x94, 0x58, 0xd1, 0xe8, 0x79, 0x41, 0x63, 0x7b, 
0xee, 0xe9, 0x8e, 0x1f, 0x35, 0xbf, 0x81, 0x6e, 
0x3c, 0x7b, 0x45, 0x53, 0x8a, 0x49, 0x54, 0x3d, 
0x2c, 0x04, 0xd7, 0xed, 0xfb, 0x55, 0xbc, 0x33, 
0x57, 0x2b, 0xbc, 0x53, 0xda, 0xe8, 0x74, 0x5c, 
0x98, 0xc9, 0x96, 0x2d, 0x5f, 0xcc, 0x0d, 0x23, 
0x7e, 0x4c, 0x29, 0xa8, 0x8f, 0x2b, 0x28, 0xb8, 
0xca, 0xfc, 0x8b, 0x6a, 0x0d, 0xd4, 0x56, 0x48, 
0x10, 0x30, 0xd5, 0xc1, 0xf5, 0x5a, 0xd4, 0xd3, 
0xa9, 0xd2, 0x30, 0xb3, 0xda, 0x1d, 0x88, 0xfc, 
0x4a, 0x8b, 0x76, 0xa6, 0x94, 0x43, 0x0b, 0x4e, 
0xad, 0x71, 0x2c, 0x79, 0x82, 0xe8, 0x6d, 0xe0, 
0xbd, 0xa5, 0x4c, 0x4c, 0x9f, 0x6f, 0xe6, 0x67, 
0x2d, 0xe0, 0x98, 0x39, 0x99, 0xc3, 0xcb, 0x6e, 
0x59, 0x14, 0x20, 0xe4, 0x7c, 0x93, 0x76, 0x46, 
0xde, 0xe1, 0x1e, 0x39, 0x5b, 0x54, 0x35, 0xd5, 
0xbd, 0x84, 0x7d, 0x18, 0xc7, 0x51, 0x86, 0x54, 
0xf2, 0xa6, 0xa6, 0x7b, 0xc2, 0xed, 0x84, 0x23, 
0x81, 0xf6, 0xf9, 0xbd, 0x0c, 0xdf, 0x11, 0xca, 
0xa8, 0x4e, 0x90, 0x69, 0x83, 0x5f, 0x7c, 0x44, 
0x1d, 0xb1, 0x1c, 0xaf, 0xd2, 0x91, 0x42, 0x57, 
0xdf, 0x94, 0x69, 0x9e, 0x40, 0xfc, 0x13, 0xdb, 
0x45, 0x93, 0xf2, 0xc9, 0xba, 0x1a, 0x1f, 0x4b, 
0xf1, 0x1b, 0x5f, 0x24, 0xe3, 0x99, 0x6e, 0xf4, 
0x58, 0x1a, 0x95, 0x06, 0x83, 0xf2, 0x5d, 0xd8, 
0x69, 0xd9, 0xd0, 0xa9, 0xb1, 0xf7, 0xbb, 0x93, 
0xe2, 0xb1, 0x22, 0x08, 0xe6, 0x10, 0x39, 0x2c, 
0xd4, 0x34, 0x0f, 0x49, 0x1a, 0xf9, 0xba, 0x84, 
0x3a, 0xbd, 0xc9, 0x47, 0x8b, 0x5f, 0x1e, 0x2f, 
0x7d, 0xd1, 0x89, 0xb5, 0x25, 0x02, 0xcc, 0xf6, 
0x79, 0xf3, 0x8b, 0x6e, 0x5d, 0xd4, 0xef, 0xdc, 
0xea, 0x1f, 0x68, 0xec, 0xd4, 0x89, 0x45, 0x0d, 
0x18, 0x43, 0xe5, 0xac, 0x81, 0xf5, 0xf1, 0x39 };

char server_7[] = { // Reliable(ChunkTail) of game.s2c_packet.ArenaSettings
0x00, 0x03, 0xf9, 0x8b, 0xe2, 0xbb, 0x86, 0x62, 
0x71, 0x5a, 0xf2, 0x37, 0x16, 0x66, 0x81, 0x85, 
0x5b, 0x42, 0x54, 0xb3, 0xbf, 0xd2, 0x37, 0xff, 
0x8e, 0xc4, 0x82, 0x62, 0x7f, 0xe7, 0x25, 0xbe, 
0x7d, 0x3a, 0x9b, 0x41, 0x5f, 0x2d, 0xc0, 0x75, 
0x56, 0x6c, 0x07, 0xab, 0x42, 0xac, 0x1e, 0x24, 
0xc7, 0x7f, 0xfc, 0xc9, 0x18, 0xcb, 0x75, 0x00, 
0x10, 0xa1, 0x78, 0x46, 0x08, 0x91, 0x52, 0xce, 
0x09, 0x09, 0x34, 0xf7, 0x57, 0x87, 0x3e, 0x05, 
0xd8, 0x01, 0x96, 0x01, 0x87, 0x51, 0xe0, 0x62, 
0x53, 0x6e, 0xdf, 0x8c, 0xfe, 0xcf, 0x9f, 0x27, 
0xff, 0x8f, 0x02, 0xf8, 0x08, 0x66, 0x3b, 0xb8, 
0x53, 0x98, 0x2f, 0xca, 0x0a, 0xb2, 0x67, 0x10, 
0xe9, 0xe4, 0x65, 0xa3, 0xee, 0x00, 0x64, 0x8a, 
0xd9, 0xd3, 0x0e, 0xfb, 0x32, 0xb9, 0x49, 0x82, 
0xb2, 0xd2, 0x80, 0x82, 0xeb, 0xce, 0x06, 0xb7, 
0xe0, 0x03, 0x2e, 0xfb, 0x08, 0x01, 0x95, 0x19, 
0xce, 0x48, 0x5b, 0xd3, 0xc1, 0xac, 0x49, 0x47, 
0x00, 0xc7, 0xfc, 0x08, 0xa7, 0xcb, 0x49, 0x83, 
0x60, 0x42, 0xe2, 0xe5, 0xb2, 0x0c, 0xda, 0x3a, 
0xfe, 0x44, 0x44, 0x41, 0xfd, 0xc9, 0x18, 0xc8, 
0x7b, 0x7b, 0x37, 0x36, 0x44, 0x94, 0x25, 0x21, 
0x7d, 0xc3, 0xea, 0x67, 0x3c, 0x00, 0x4d, 0x37, 
0xa3, 0x8a, 0x7a, 0x4e, 0x36, 0xcd, 0x7f, 0xea, 
0x07, 0xbb, 0x8e, 0x4d, 0x09, 0x6d, 0x6d, 0x06, 
0xf9, 0x5c, 0xb5, 0x9f, 0x8d, 0x32, 0xb7, 0x88, 
0xe5, 0xc4, 0x6f, 0xd3, 0x49, 0xd6, 0x8e, 0x92, 
0x07, 0xf5, 0x67, 0x4b, 0xb1, 0x87, 0x36, 0x8a, 
0xe7, 0xf4, 0x7b, 0xf0, 0x4a, 0xf3, 0xc9, 0x62, 
0x9b, 0xfb, 0x8e, 0x00, 0x5c, 0xa1, 0x81, 0x71, 
0x05, 0x23, 0x45, 0x4c, 0xf3, 0x1c, 0x57, 0x22, 
0x1d, 0xb9, 0xd5, 0xf2, 0x1a, 0xf0, 0xbe, 0x2c, 
0xca, 0x8c, 0xbe, 0x4c, 0x82, 0x4a, 0x12, 0x43, 
0x9f, 0x7e, 0xdd, 0x32, 0xcc, 0x71, 0x74, 0x3c, 
0xc1, 0xf0, 0xc6, 0xb7, 0xd2, 0x90, 0x17, 0xa0, 
0x2e, 0x4c, 0x40, 0x73, 0xa2, 0x64, 0xa1, 0x51, 
0x77, 0x80, 0xd6, 0xd9, 0x74, 0xea, 0xc4, 0xcb, 
0x84, 0x6f, 0x5e, 0xaf, 0xa7, 0xa7, 0x67, 0xe0, 
0x2f, 0x31, 0x74, 0xb7, 0x64, 0xfe, 0xeb, 0x59, 
0xc9, 0xce, 0x96, 0x6c, 0x1f, 0x57, 0x7e, 0xf5, 
0x52, 0x1a, 0xe7, 0x5d, 0xe0, 0xd1, 0xf5, 0x7d, 
0x53, 0x5e, 0x17, 0x23, 0x6e, 0x7c, 0x82, 0x75, 
0x39, 0xab, 0x15, 0xff, 0xa8, 0x3e, 0x8b, 0x5d, 
0x85, 0x4c, 0xd5, 0x22, 0x77, 0xe6, 0x9a, 0xc8, 
0xb1, 0x37, 0x9c, 0x04, 0xe7, 0xe8, 0x98, 0xbb, 
0x42, 0x1f, 0x99, 0x94, 0x7d, 0x54, 0x02, 0xc6, 
0x0d, 0x4f, 0x27, 0x5a, 0x6e, 0x65, 0x4f, 0x2d, 
0xfe, 0x4b, 0x50, 0x87, 0xf5, 0x59, 0x54, 0xa9, 
0x75, 0xb7, 0xc0, 0x43, 0x54, 0x95, 0x42, 0xbe, 
0x59, 0x90, 0x7d, 0x77, 0x1e, 0xdf, 0xd7, 0x35, 
0xdc, 0xb9, 0x36, 0x27, 0xa7, 0x37, 0xbf, 0xa5, 
0xcf, 0x36, 0xd2, 0xca, 0xa1, 0xb5, 0xd1, 0x1a, 
0x8b, 0x36, 0xbc, 0xe9, 0x80, 0xd1, 0xdc, 0x3d, 
0x6a, 0xfa, 0xa5, 0x4d, 0xd7, 0xcd, 0x82, 0x76, 
0x4e, 0x8b, 0xef, 0xed, 0xac, 0x2a, 0xe4, 0xc8, 
0x32, 0x03, 0xac, 0xa9, 0x58, 0xc8, 0xfc, 0x64, 
0x76, 0x8a, 0x22, 0x1e, 0x0e, 0xd8, 0x50, 0x76, 
0xd6, 0xd2, 0xc3, 0xea, 0x72, 0x01, 0x48, 0x49, 
0x4a, 0xf0, 0x93, 0x61, 0x9e, 0x27, 0x43, 0xd6, 
0x14, 0xec, 0xd1, 0x8e };

char server_8[] = { /* Cluster of 
Reliable(game.s2c_packet.PlayerID),
Reliable(game.s2c_packet.PlayerEntering),
Reliable(game.s2c_packet.PlayerEntering),
Reliable(game.s2c_packet.MapInformation),
Reliable(game.s2c_packet.BrickDropped),
Reliable(game.s2c_packet.LoginComplete),
Reliable(game.s2c_packet.SetShipType),
Reliable(game.s2c_packet.SecurityRequest),
 */
0x00, 0x0e, 0xf4, 0x8b, 0xe1, 0xba, 0x8b, 0x6b, 
0x6b, 0x5a, 0xc6, 0x3e, 0x7d, 0x66, 0x72, 0x80, 
0x3c, 0x42, 0xe7, 0xb5, 0x58, 0xc1, 0xe1, 0x9c, 
0x1f, 0xfb, 0x39, 0x6c, 0x8d, 0xb9, 0xf3, 0xd2, 
0xed, 0x07, 0x4d, 0x2d, 0xcf, 0x11, 0x16, 0x1d, 
0x4e, 0xf0, 0x87, 0xc2, 0x5a, 0x30, 0x9e, 0x4d, 
0xdf, 0xe3, 0x7c, 0xa0, 0x00, 0x57, 0xf5, 0x69, 
0x08, 0x3d, 0xf8, 0x2f, 0xb0, 0x02, 0xd2, 0xa7, 
0x75, 0x93, 0xb4, 0x9e, 0x2b, 0x1d, 0xbf, 0x6c, 
0xd0, 0x84, 0x25, 0x68, 0xa3, 0xd5, 0x9e, 0xf4, 
0x8d, 0xea, 0x37, 0x5c, 0xe4, 0x41, 0xa1, 0xf0, 
0xe4, 0x01, 0x67, 0x25, 0xda, 0x8c, 0x1b, 0x12, 
0x3d, 0x17, 0x22, 0x15, 0x4d, 0x3c, 0x78, 0xcf, 
0x1c, 0x66, 0x1f, 0x78, 0xcd, 0x84, 0x09, 0x50, 
0xeb, 0x57, 0xc8, 0x2c, 0x64, 0x39, 0x5a, 0x53, 
0xcc, 0x52, 0x91, 0x53, 0x6f, 0x4e, 0xb1, 0x66, 
0x00, 0x83, 0x29, 0x2e, 0x78, 0x80, 0x4e, 0xc9, 
0xbf, 0xc9, 0xfd, 0x03, 0xa9, 0x21, 0xd3, 0xce, 
0xe1, 0x4a, 0x1b, 0x81, 0x66, 0xba, 0x63, 0x0a, 
0xb8, 0x33, 0xe6, 0x6c, 0x5e, 0x7a, 0x66, 0xb8, 
0x1e, 0x1b, 0x51, 0xb0, 0x9a, 0xe6, 0x21, 0x4d, 
0x69, 0x39, 0x0f, 0xb0, 0x56, 0xd6, 0x1c, 0xa6, 
0x6e, 0x81, 0xf4, 0xc7, 0x3e, 0xf4, 0x54, 0x97, 
0x2a, 0xf6, 0x09, 0xef, 0xbf, 0x90, 0x0b, 0x4b, 
0x8d, 0xef, 0xfa, 0xec, 0x83, 0x3b, 0x0e, 0xa7, 
0x70, 0x00, 0xd6, 0x3e, 0x54, 0x42, 0x4a, 0xeb, 
0xbb, 0x39, 0xc4, 0xfc, 0x36, 0x25, 0xe6, 0x77, 
0x1f, 0x69, 0x0f, 0xae, 0x11, 0x10 };

char client_15[] = { /* game.c2s_packet.Position
.rotation: 0
.time: 2014830830
.dx: 0
.y_pixels: 0
.checksum: 98
.status: 0
.x_pixels: 0
.dy: 0
.bounty: 0
.energy: 0
.weapon_info: 0  */
0x03, 0xfd, 0x65, 0x02, 0xac, 0xfa, 0x85, 0x88, 
0x4d, 0xbb, 0xb2, 0xd8, 0x71, 0x0c, 0x09, 0x99, 
0x55, 0x99, 0x3f, 0xf5, 0xd6, 0xfb, 0xb0, 0xc3, 
0xc1, 0x4f, 0x2f, 0x32, 0xa2, 0xe9, 0xf6, 0x31 };

char server_9[] = { /* Reliable(game.s2c_packet.FlagPosition) */
0x00, 0x03, 0xf6, 0x8b, 0xe2, 0xbb, 0x9b, 0x6b, 
0x68, 0x2b, 0xd8, 0xe6, 0x39, 0x17, 0x6f };

char server_10[] = { /* Cluster of 4 Reliable(game.s2c_packet.FlagPosition) */
0x00, 0x0e, 0xf2, 0x8b, 0xe1, 0xb7, 0x8d, 0x6b, 
0x6b, 0x44, 0xcd, 0x3e, 0xc0, 0x79, 0x8c, 0x84, 
0x7e, 0xa2, 0x16, 0xb2, 0x11, 0x2c, 0x74, 0xf2, 
0x20, 0x29, 0xc2, 0x6d, 0x2e, 0x0b, 0x89, 0xb1, 
0xd2, 0x29, 0x38, 0x4e, 0xf3, 0x31, 0x63, 0x7e, 
0x72, 0xc2, 0xf1, 0xa1, 0x62, 0x00, 0x17, 0x2f, 
0x18, 0x2c, 0xfa, 0xc2, 0xc4, 0x97, 0x73, 0x0b, 
0xcc, 0xef, 0x7a, 0x4d, 0x64, 0xd2, 0xae, 0xc4, 
0x5e, 0xbc };

char server_11[] = { /* Reliable(game.s2c_packet.ChatMessage):
.type: 0
.sound: 0
.sending_player_id: 65535
.message: Welcome to ASWZ.  http://aswz.org  */
0x00, 0x03, 0xed, 0x8b, 0xe2, 0xbb, 0x95, 0x6b, 
0x68, 0xa5, 0x2b, 0x69, 0x5d, 0xf5, 0xff, 0xbd, 
0x71, 0xb4, 0x4a, 0xff, 0x72, 0x17, 0x69, 0xec, 
0x14, 0x5a, 0xf3, 0x53, 0xc5, 0x11, 0x21, 0xfa, 
0xb6, 0xf6, 0xb0, 0x2a, 0xf5, 0x93, 0x9c, 0x60, 
0x5a, 0x1d, 0x7f, 0xd8, 0x4e };

char server_14[] = { // game.s2c_packet.BallPosition
0x2e, 0xfd, 0x87, 0xc0, 0x14, 0x9c, 0xf1, 0x5a, 
0x9c, 0x2d, 0x5b, 0xf5, 0x75, 0x00, 0xf7, 0xcc };

char client_27[] = { /* game.c2s_packet.Position
.rotation: 0
.time: 2014830883
.dx: 0
.y_pixels: 0
.checksum: 174
.status: 0
.x_pixels: 0
.dy: 0
.bounty: 0
.energy: 0
.weapon_info: 0  */
0x03, 0xfd, 0xa8, 0x03, 0xac, 0xfa, 0x48, 0x89, 
0x4d, 0xbb, 0xb3, 0xd9, 0x71, 0x0c, 0x08, 0x98, 
0x55, 0x99, 0x3e, 0xf4, 0xd6, 0xfb, 0xb1, 0xc2, 
0xc1, 0x4f, 0x2e, 0x33, 0xa2, 0xe9, 0xf7, 0x30 };

char client_28[] = { /* game.c2s_packet.Position
.rotation: 0
.time: 2014830934
.dx: 0
.y_pixels: 0
.checksum: 219
.status: 0
.x_pixels: 0
.dy: 0
.bounty: 0
.energy: 0
.weapon_info: 0  */
0x03, 0xfd, 0xdd, 0x03, 0xac, 0xfa, 0x3d, 0x89, 
0x4d, 0xbb, 0xb3, 0xd9, 0x71, 0x0c, 0x08, 0x98, 
0x55, 0x99, 0x3e, 0xf4, 0xd6, 0xfb, 0xb1, 0xc2, 
0xc1, 0x4f, 0x2e, 0x33, 0xa2, 0xe9, 0xf7, 0x30 };

char client_31[] = { // Reliable(game.c2s_packet.LeaveArena)
0x00, 0x03, 0xff, 0x8b, 0xe2, 0xbb, 0x82 };

char server_15[] = { // core.packet.ReliableACK
0x00, 0x04, 0xff, 0x8b, 0xe2, 0xbb };

char client_32[] = { // core.packet.Disconnect
0x00, 0x07 };

char server_16[] = { // core.packet.Disconnect
0x00, 0x07 };

