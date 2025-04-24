

public class Benchmark6 {
    public static void main(String[] args) {
        // fetch input
        Long input_1_0 = Long.valueOf(args[0]);
        Long input_2_0 = Long.valueOf(args[1]);


        // Perform computation         
        String output_1 = Long.toOctalString(input_1_0);
        String output_2 = Long.toOctalString(input_2_0);

        
        // Compare output
        if (output_1.equals("1777036512664136325434") && output_2.equals("152175020141733")) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

