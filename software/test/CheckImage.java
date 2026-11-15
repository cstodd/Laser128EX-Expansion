import com.webcodepro.applecommander.storage.*;
import java.nio.file.*;
import java.util.*;

public class CheckImage {
    public static void main(String[] a) throws Exception {
        Disk disk = new Disk(a[0]);
        Path dist = Paths.get(a[1]);
        int bad = 0;
        for (FormattedDisk fd : disk.getFormattedDisks()) {
            System.out.println("Volume: " + fd.getDiskName() + "  format: " + fd.getFormat()
                + "  free: " + fd.getFreeSpace() + "  used: " + fd.getUsedSpace());
            for (FileEntry fe : fd.getFiles()) {
                byte[] data = fe.getFileData();
                System.out.printf("  %-13s %-4s %6d bytes  addr $%04X%n", fe.getFilename(), fe.getFiletype(),
                    data.length, ((com.webcodepro.applecommander.storage.os.prodos.ProdosFileEntry) fe).getAuxiliaryType());
                Path p = dist.resolve(fe.getFilename());
                if (Files.exists(p)) {
                    boolean same = Arrays.equals(Files.readAllBytes(p), data);
                    System.out.println("      matches build output: " + same);
                    if (!same) bad++;
                }
                if (fe.getFiletype().equals("BAS")) {
                    byte[] listing = fe.getSuggestedFilter().filter(fe);
                    System.out.println("      --- AppleCommander listing ---");
                    for (String l : new String(listing).split("\n")) System.out.println("      " + l);
                }
            }
        }
        System.exit(bad == 0 ? 0 : 1);
    }
}
