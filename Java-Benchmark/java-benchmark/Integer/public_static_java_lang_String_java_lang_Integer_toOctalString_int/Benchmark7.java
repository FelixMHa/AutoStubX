

public class Benchmark7 {
    public static void main(String[] args) {
        // fetch input
        Integer input_1_0 = Integer.valueOf(args[0]);
        Integer input_2_0 = Integer.valueOf(args[1]);


        // Perform computation         
        String output_1 = Integer.toOctalString(input_1_0);
        String output_2 = Integer.toOctalString(input_2_0);

        
        // Compare output
        if (output_1.equals("10533240005") && output_2.equals("37777641750")) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

